from collections import Counter
import redis
import threading
import uwsgi


db = redis.StrictRedis(host='localhost', port=6379, db=0)

commit_queue = []


def commit_enqueued():
    if not commit_queue:
        return
    with db.pipeline(transaction=False) as p:
        z = 0
        while commit_queue:
            prefix, values = commit_queue.pop()
            while values:
                id, n = values.popitem()
                p.incrby("%s_%s" % (prefix, id), n)
                z += n
        p.execute()
        if z:
            print "Committed", z, "changes"

# def commit_watcher():
#   print "Commit watcher started"
#   while 1:
#       if commit_queue:
#           commit_enqueued()
#       time.sleep(random.uniform(1, 4))

# def start_commit_watcher():
#   threading.Thread(target=commit_watcher).start()


class BannerServer(object):

    def __init__(self, next_application):
        self.next_application = next_application
        self.img_cache = {}
        self.url_cache = {}

        self.imp_cache = Counter()
        self.clk_cache = Counter()

    def commit(self):
        if self.imp_cache or self.clk_cache:
            imp_cache = dict(self.imp_cache)
            self.imp_cache.clear()
            clk_cache = dict(self.clk_cache)
            self.clk_cache.clear()
            if imp_cache:
                commit_queue.append(("imp", imp_cache))
            if clk_cache:
                commit_queue.append(("clk", clk_cache))
            threading.Thread(target=commit_enqueued).start()

    def get_url(self, banner_id):
        url = self.url_cache.get(banner_id)
        if not url:
            self.url_cache[banner_id] = url = db.get("url_%s" % banner_id)
        return url

    def get_img(self, banner_id):
        img = self.img_cache.get(banner_id)
        if not img:
            self.img_cache[banner_id] = img = db.get("img_%s" % banner_id)
        return img

    def serve(self, path_info):
        pfx = path_info[:3]
        banner_id = path_info[3:36].strip("/")

        if pfx == "/i/":
            img = self.get_img(banner_id)
            if img:
                self.imp_cache[banner_id] += 1
                return ("200 OK", {"X-Accel-Redirect": img}, "OK")
            else:
                return ("404 Not Found", {}, "404")

        if pfx == "/c/":
            url = self.get_url(banner_id)
            if url:
                self.clk_cache[banner_id] += 1
                return ("302 OK", {"Location": url}, url)
            else:
                return ("404 Not Found", {}, "404")

    def __call__(self, environ, start_response):
        resp = self.serve(environ["PATH_INFO"])
        if resp:
            resp[1]["Content-Length"] = str(len(resp[2]))
            start_response(resp[0], resp[1].items())
            return resp[2]
        else:
            return self.next_application(environ, start_response)


def commit_banners(x):
    banner_server.commit()

from wsgiref.simple_server import demo_app
application = banner_server = BannerServer(demo_app)

uwsgi.register_signal(42, 'workers', commit_banners)
uwsgi.add_rb_timer(42, 5)
