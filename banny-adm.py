import argparse
import redis

db = redis.StrictRedis(host='localhost', port=6379, db=0)


def show_stats(id):
    img, url, impr, clicks = db.mget(
        "img_%s" % id,
        "url_%s" % id,
        "imp_%s" % id,
        "clk_%s" % id
    )
    print "ID:          %s" % id
    print "Image:       %s" % img
    print "URL:         %s" % url
    print "Impressions: %7d" % int(impr or 0)
    print "Clicks:      %7d" % int(clicks or 0)
    if img:
        db.sadd("banners", id)


def save(id, image, url, reset=False):
    db.sadd("banners", id)
    db.set("img_%s" % id, image)
    db.set("url_%s" % id, url)
    if reset:
        db.set("imp_%s" % id, 0)
        db.set("clk_%s" % id, 0)


def show_all_stats():
    for id in sorted(db.smembers("banners")):
        show_stats(id)
        print


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id")
    ap.add_argument("--url")
    ap.add_argument("--image")
    ap.add_argument("--reset", action="store_true")

    args = ap.parse_args()

    if args.id and args.image and args.url:
        save(args.id, args.image, args.url, args.reset)
    elif args.id:
        show_stats(args.id)
    else:
        show_all_stats()

if __name__ == '__main__':
    main()
