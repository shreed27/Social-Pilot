"""Command line helpers.

  python cli.py generate insta_main [--format carousel]   # run the agent pipeline once
  python cli.py fill                                        # top up every page's queue
  python cli.py publish | engage | metrics                  # run one job now
  python cli.py pages                                       # list configured pages
  python cli.py slack-test | slack-digest                   # check the Slack webhook / send today's report now
  python cli.py xbird-scout x_main                          # what's working on X in this niche (needs XBIRD_ENABLED)
"""
import argparse
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("page_id")
    g.add_argument("--format")
    g.add_argument("--pillar")
    for name in ("fill", "publish", "engage", "metrics", "pages", "slack-test", "slack-digest"):
        sub.add_parser(name)
    xs = sub.add_parser("xbird-scout")
    xs.add_argument("page_id")
    a = ap.parse_args()

    if a.cmd == "generate":
        from app.agents.graph import generate_post
        r = generate_post(a.page_id, pillar=a.pillar, fmt=a.format)
        print(json.dumps({k: r.get(k) for k in ("draft_id", "pillar", "format", "topic", "media", "log")},
                         indent=2, ensure_ascii=False))
    elif a.cmd == "fill":
        from app.scheduler import keep_queue_full
        print("drafts created:", keep_queue_full())
    elif a.cmd == "publish":
        from app.publisher import publish_due
        print("published:", publish_due())
    elif a.cmd == "engage":
        from app.engagement import scan_comments
        print("reply drafts:", scan_comments())
    elif a.cmd == "metrics":
        from app.analytics import collect_metrics
        collect_metrics()
        print("metrics collected")
    elif a.cmd == "slack-test":
        from app import slack
        print("sent" if slack.send("👋 SocialPilot is connected to this channel.") else "not sent: set SLACK_WEBHOOK_URL in .env")
    elif a.cmd == "slack-digest":
        from app import slack
        text, blocks = slack.build_digest()
        print(text)
        print("sent to Slack" if slack.send(text, blocks) else "not sent: set SLACK_WEBHOOK_URL in .env")
    elif a.cmd == "xbird-scout":
        from app.pages import get_page
        from app.settings import get_settings
        from app.sources import xbird
        if not get_settings().xbird_enabled:
            print("XBIRD_ENABLED is false in .env"); return
        page = get_page(a.page_id)
        print("planned calls:", *[f"  {n} {args}" for n, args in xbird.plan_calls(page)], sep="\n")
        posts = xbird.scout(page)
        print(f"\n{len(posts)} posts · spent today ${xbird.spent_today():.3f}\n")
        for p in posts:
            print(f"{p['multiple']:>6}×  hook {p['hook_score']:>5}  @{p['author'] or '?':<18} {p['likes']:>7} likes  {p['text'][:90]!r}")
    elif a.cmd == "pages":
        from app.pages import load_pages
        for p in load_pages().values():
            print(f"{p.id:15} {p.platform:10} {p.handle:25} {p.posts_per_week}/wk  formats={p.formats}")


if __name__ == "__main__":
    main()
