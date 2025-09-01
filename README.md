# lukhed_x

A custom tweepy wrapper for posting on X (formerly Twitter) with built-in key management and enhanced functionality. 
Used by @grindSunday and @popPunkPoets bots.

## Features

- **Easy X API Integration**: Simplified interface for X API v1 and v2 endpoints
- **Flexible Key Management**: Store API credentials locally or in GitHub repositories
- **Post Management**: Create, delete, and manage posts with media support
- **Image Upload Support**: Easy media attachment for posts

## Installation

```bash
pip install lukhed-x
```

## Quick Start

### Initial Setup

```python
from lukhed_x import X

# First-time setup - this will prompt for your X API credentials
x_client = X(handle="your_handle", x_api_setup=True)
```

### Basic Usage

```python
from lukhed_x import X

# Initialize client (after initial setup)
x_client = X(handle="your_handle")

# Create a simple tweet
result = x_client.create_tweet("Hello, world!")
if not result["error"]:
    print(f"Tweet posted: {result['url']}")
    print(f"Tweet ID: {result['tweetID']}")

# Create tweet with image
result = x_client.create_tweet(
    "Check out this image!", 
    image_data="path/to/image.jpg"
)

# Reply to a tweet
result = x_client.create_tweet(
    ".@username Thanks for the great post!",
    reply_to_tweet_id="1234567890"
)

# Quote tweet
result = x_client.create_tweet(
    "Great point!",
    quote_tweet_id="1234567890"
)

# Delete a tweet
result = x_client.delete_tweet("your_tweet_id")
```

## X API Setup

Before using lukhed_x, you need to set up an X Developer account:

1. Create a free developer account at [developer.x.com](https://developer.x.com/en)
2. Create a new app and generate your API credentials
3. You'll need:
   - **API Key**
   - **API Secret** 
   - **Access Token**
   - **Access Token Secret**

For detailed instructions, visit: [X API Getting Started Guide](https://docs.x.com/x-api/getting-started/getting-access)

## Key Management Options

lukhed_x supports two key management strategies:

### Local Storage
```python
x_client = X(handle="your_handle", key_management="local")
```
Stores API credentials in your local file system.

### GitHub Storage (Default)
```python
x_client = X(handle="your_handle", key_management="github")
```
Stores API credentials in a private GitHub repository, allowing access across different devices. You will need a 
github access token: 
[Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)

## Error Handling

All API methods return a consistent error structure:

```python
result = x_client.create_tweet("Hello!")
if result["error"]:
    print("Function Error:", result["errorData"]["functionError"])
    print("Tweepy Error:", result["errorData"]["tweepyError"])
else:
    print("Success:", result["url"])
```

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please open an issue on the GitHub repository.

---
**Note**: This wrapper is designed for legitimate bot usage and follows X's Terms of Service. 
Please ensure your bot complies with X's automation rules and rate limits.
