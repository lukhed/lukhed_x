# lukhed_x

A custom tweepy wrapper for the X API v2 with built-in key management via `LukhedAuth`.
Used by @grindSunday and @popPunkPoets bots.

## Features

- **X API v2**: v1.1 endpoints are gone, this wrapper is v2 only
- **Flexible Key Management**: Store API credentials locally or in a private GitHub repo
- **Cost Aware**: every method documents what it costs to call
- **Posts, Users, Engagement, Lists, DMs and Media**

## Installation

```bash
pip install lukhed-x
```

## Costs

X retired the free tier in 2026. Every call costs credits, which you buy at
[console.x.com](https://console.x.com). Full table:
[X API pricing](https://docs.x.com/x-api/getting-started/pricing).

The one to watch:

| Action | Cost |
|---|---|
| Create a post | **$0.015** |
| Create a post **containing a URL** | **$0.200** |
| Owned reads (your own posts, followers, mentions, lists) | $0.001 |
| Post / list reads | $0.005 |
| User and follower reads | $0.010 |
| Likes, reposts, follows, mutes, DMs | $0.015 |
| Undoing any of those | $0.010 |

A link in your post text costs **13x** a plain post. Keep URLs out of automated posts unless you
mean it.

Set a spending cap in the developer console before running any bot.

## Quick Start

### Initial Setup

```python
from lukhed_x import X

# First run prompts for your X API credentials, then stores them
x_client = X(handle="your_handle")
```

### Basic Usage

```python
from lukhed_x import X

x_client = X(handle="your_handle")

# Create a post
result = x_client.create_post("Hello, world!")
if not result["error"]:
    print(f"Posted: {result['url']}")
    print(f"Post ID: {result['postID']}")

# Post with an image
upload = x_client.upload_media("path/to/image.jpg")
x_client.create_post("Check out this image!", media_ids=[upload["mediaID"]])

# Reply
x_client.create_post(".@username Thanks for the great post!", reply_to_post_id="1234567890")

# Poll
x_client.create_post("Who wins?", poll_options=["Ravens", "Steelers"], poll_duration_minutes=1440)

# Read your own timeline (owned read, $0.001)
x_client.get_my_posts(max_results=10)

# Delete
x_client.delete_post("your_post_id")
```

## Available Methods

**Posts (write)**: `create_post`, `delete_post`, `hide_reply`, `unhide_reply`

**Posts (read)**: `get_post`, `get_posts`, `get_my_posts`, `get_user_posts`, `get_my_mentions`,
`get_home_timeline`, `search_recent_posts`, `get_recent_post_counts`, `get_quote_posts`,
`get_reposters`, `get_liking_users`

**Engagement**: `like_post`, `unlike_post`, `repost`, `unrepost`, `follow_user`, `unfollow_user`,
`mute_user`, `unmute_user`

**Users**: `get_me`, `get_user`, `get_users`, `get_my_followers`, `get_my_following`,
`get_user_followers`, `get_user_following`, `get_my_liked_posts`, `get_my_muted`, `get_my_blocked`

**Lists**: `create_list`, `update_list`, `delete_list`, `add_list_member`, `remove_list_member`,
`get_list`, `get_list_posts`, `get_my_lists`

**DMs**: `send_dm`, `get_dm_events`

**Media**: `upload_media`

Read methods accept any [X API v2 field/expansion parameter](https://docs.x.com/x-api/fundamentals/fields)
as a keyword argument, e.g. `get_my_posts(max_results=20, tweet_fields=["public_metrics"])`.

## X API Setup

1. Create a developer account at [developer.x.com](https://developer.x.com/en)
2. Buy credits at [console.x.com](https://console.x.com) and set a spending cap
3. Create an app with **Read and Write** permissions and generate credentials
4. You'll need:
   - **API Key**
   - **API Secret**
   - **Access Token**
   - **Access Token Secret**
   - **Bearer Token** (optional, only for app-only endpoints like `get_recent_post_counts`)

For detailed instructions, visit the
[X API Getting Started Guide](https://docs.x.com/x-api/getting-started/getting-access).

## Key Management Options

Authentication is handled by `LukhedAuth` under the project name `xapi`, keyed by handle, so one
install can drive multiple bot accounts.

### GitHub Storage (Default)
```python
x_client = X(handle="your_handle", key_management="github")
```
Stores credentials in a private GitHub repository, allowing access across different devices. You
will need a github access token:
[Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)

### Local Storage
```python
x_client = X(handle="your_handle", key_management="local")
```
Stores credentials in your local file system.

### Provide Auth Directly
```python
x_client = X(handle="your_handle", provide_auth={
    "apiKey": "...", "apiSecret": "...",
    "accessToken": "...", "accessTokenSecret": "..."
})
```

## Error Handling

All methods return a consistent structure:

```python
result = x_client.create_post("Hello!")
if result["error"]:
    print("Function Error:", result["errorData"]["functionError"])
    print("Tweepy Error:", result["errorData"]["tweepyError"])
else:
    print("Success:", result["url"])
```

## Notes and Limitations

- **Auth**: OAuth 1.0a user context. X still supports it for v2, but their docs now lead with
  OAuth 2.0, so expect a migration eventually.
- **Media upload**: uses the v2 chunked flow (`initialize` / `append` / `finalize`). X documents
  those endpoints for OAuth 2.0 with the `media.write` scope, so OAuth 1.0a may return a 403.
- **Quote posts**: `quote_post_id` now requires an Enterprise plan.
- **Bookmarks and Spaces**: omitted, they need OAuth 2.0 user context.
- **Blocking**: X removed the v2 write endpoints. `get_my_blocked` reads only.
- **Deprecated but kept**: `create_tweet`, `delete_tweet` and `get_my_user_info` still work and
  return the same keys as before. `create_tweet(image_data=...)` now expects a file path.

## Migrating from 0.1.x

- `X(..., x_api_setup=True)` is gone. Setup runs automatically when no keys are found for a handle.
- v1.1 methods and the version switching helpers are gone.
- Existing stored keys keep working. Re-run setup only if you want to add a bearer token.

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please open an issue on the GitHub repository.

---
**Note**: This wrapper is designed for legitimate bot usage and follows X's Terms of Service.
Please ensure your bot complies with X's automation rules and rate limits.
