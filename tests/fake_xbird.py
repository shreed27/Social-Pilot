"""Stand-in for the xbird MCP server (same tool names, X-shaped JSON), used by the tests."""
import json
import os

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("fake-xbird")
LOG = os.environ.get("FAKE_XBIRD_LOG", "")


def _log(name, args):
    if LOG:
        with open(LOG, "a") as f:
            f.write(json.dumps({"tool": name, "args": args}) + "\n")


def tweet(i, author, text, likes, replies, rts=0, bm=0):
    return {"rest_id": str(i), "core": {"user": {"legacy": {"screen_name": author}}},
            "legacy": {"full_text": text, "favorite_count": likes, "reply_count": replies,
                       "retweet_count": rts, "quote_count": 0, "bookmark_count": bm}}


@mcp.tool()
def search_tweets(query: str, count: int = 20) -> str:
    _log("search_tweets", {"query": query, "count": count})
    rows = [tweet(1, "bigacct", "Five study tips for exams", 900, 10, 20, 5),
            tweet(2, "bigacct", "Another generic tip thread", 1000, 12, 25, 6),
            tweet(3, "bigacct", "Motivation monday", 950, 8, 18, 4),
            tweet(4, "smallacct", "I failed DBMS twice. The third time I stopped re-reading and did this.", 4200, 610, 300, 900),
            tweet(5, "smallacct", "ok", 12, 1),
            tweet(6, "smallacct", "lunch", 15, 2)]
    return json.dumps({"data": {"tweets": rows}})


@mcp.tool()
def get_user_tweets_by_handle(handle: str, count: int = 20) -> str:
    _log("get_user_tweets_by_handle", {"handle": handle})
    return json.dumps([tweet(10, handle, "Stop highlighting. Start testing yourself.", 3000, 400, 120, 700)])


@mcp.tool()
def post_tweet(text: str) -> str:  # must never be called by SocialPilot
    _log("post_tweet", {"text": text})
    return "posted"


if __name__ == "__main__":
    mcp.run()
