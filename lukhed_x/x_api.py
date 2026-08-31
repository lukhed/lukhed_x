from typing import Optional
from lukhed_basic_utils.classCommon import LukhedAuth
from requests_oauthlib import OAuth1Session
import mimetypes
import os
import tweepy

# https://docs.tweepy.org/en/stable/client.html
# https://docs.x.com/x-api/getting-started/pricing

# X retired the free tier in 2026. Every call below costs credits, purchased at https://console.x.com
# v1.1 endpoints are gone, so this wrapper is v2 only.


class X(LukhedAuth):
    def __init__(self, handle, key_management='github', provide_auth=None):
        """
        This class is a custom tweepy wrapper for posting on X (formerly Twitter). It includes key management and
        v2 endpoints.

        Every method notes its cost. Full pricing table: https://docs.x.com/x-api/getting-started/pricing

        Parameters
        ----------
        handle : str
            The X handle to use for API requests.
        key_management : str, optional
            The key management strategy to use. Options are:
            'local' - stores/retrieve your api key on your local hard drive (working directory)
            'github' - stores/retrieves your api key in a private repo (helpful to allow access across different
            hardware)
            Default is 'github'.
        provide_auth : dict, optional
            Bypass key management by providing auth directly. Expects keys: apiKey, apiSecret, accessToken,
            accessTokenSecret and optionally bearerToken.
        """

        self.current_handle = handle
        self._parse_handle()

        if provide_auth:
            self._auth_data = {self.current_handle: provide_auth}
        else:
            # 'xapi' project name is retained so existing stored keys keep working
            super().__init__('xapi', key_management=key_management)

        if self._auth_data is None:
            self._auth_data = {}

        if self.current_handle not in self._auth_data:
            print(f"No existing X API key data found for {self.current_handle}, starting setup...")
            self._x_api_setup()

        # Objects used
        self.tweepy_api: Optional[tweepy.Client] = None
        self._user_id = None

        self._check_create_client()

    ###########################
    # Setup and auth
    def _x_api_setup(self):
        print("This is the lukhed setup for the X API. If you haven't already, you first need to setup an"
              " X api developer acccount (https://developer.x.com/en). Note X removed the free tier in 2026, so you"
              " also need credits: https://console.x.com\n"
              "To continue, you need the following from the setup:\n"
              "1. Access Token\n"
              "2. Access Token Secret\n"
              "3. Api Key\n"
              "4. Api Secret\n"
              "5. Bearer Token (optional, only needed for app-only endpoints like counts)\n"
              "If you don't know how to get these, you can find instructions here:\n"
              "https://docs.x.com/x-api/getting-started/getting-access")

        if input("\n\nAre you ready to continue (y/n)?") == 'n':
            print("OK, come back when you have setup your developer account")
            quit()

        access_token = input("Paste your access token then press enter:\n").replace(" ", "")
        access_token_secret = input("Paste your access token secret then press enter:\n").replace(" ", "")
        api_key = input("Paste your API key here:\n").replace(" ", "")
        api_secret = input("Paste your API secret here:\n").replace(" ", "")
        bearer_token = input("Paste your bearer token here (or press enter to skip):\n").replace(" ", "")

        self._auth_data[self.current_handle] = {
            'accessToken': access_token,
            'accessTokenSecret': access_token_secret,
            'apiKey': api_key,
            'apiSecret': api_secret,
            'bearerToken': bearer_token if bearer_token else None
        }

        print("\n\nThe X portion is complete! Now setting up key management with lukhed library...")
        self.kM.force_update_key_data(self._auth_data)

    def _parse_handle(self):
        # accept a handle with or without the @symbol
        if "@" not in self.current_handle:
            self.current_handle = "@" + self.current_handle

    def _check_create_client(self):
        """
        Creates the v2 client with OAuth 1.0a user context, which is required for all write endpoints.
        The bearer token is optional and only unlocks app-only endpoints (counts).
        """
        if self.tweepy_api is None:
            key_data = self._auth_data[self.current_handle]
            self.tweepy_api = tweepy.Client(consumer_key=key_data["apiKey"],
                                            consumer_secret=key_data["apiSecret"],
                                            access_token=key_data["accessToken"],
                                            access_token_secret=key_data["accessTokenSecret"],
                                            bearer_token=key_data.get("bearerToken"))

    def _get_oauth_session(self):
        key_data = self._auth_data[self.current_handle]
        return OAuth1Session(key_data["apiKey"],
                             client_secret=key_data["apiSecret"],
                             resource_owner_key=key_data["accessToken"],
                             resource_owner_secret=key_data["accessTokenSecret"])

    def _get_my_user_id(self):
        # cached, as the owned read endpoints all need the id and the lookup itself costs credits
        if self._user_id is None:
            result = self.get_me()
            if result['error']:
                return None
            self._user_id = result['twitterResponse'].data.id
        return self._user_id

    def _call(self, func, *args, **kwargs):
        """
        Wraps every tweepy call in the standard lukhed response shape.
        """
        try:
            response = func(*args, **kwargs)
        except Exception as e:
            function_defined_error_message = f"Failed while calling {func.__name__}"
            print(function_defined_error_message)
            print(e)

            return {"error": True,
                    "twitterResponse": None,
                    "errorData": {"functionError": function_defined_error_message,
                                  "tweepyError": str(e)}}

        return {"error": False,
                "twitterResponse": response,
                "errorData": None}

    #######################
    # Posts: write
    def create_post(self, post_text, reply_to_post_id=None, media_ids=None, quote_post_id=None, poll_options=None,
                    poll_duration_minutes=None, reply_settings=None, community_id=None):
        """
        Creates a post. https://docs.x.com/x-api/posts/create-post

        Cost: $0.015 per request, or $0.200 if the post text contains a URL
        https://docs.x.com/x-api/getting-started/pricing

        :param post_text:               text you want to post
        :param reply_to_post_id:        post ID you want to reply to. Note: if this is supplied,
                                        @[handle_replying_to] must be in the text for it to show up in the replies
        :param media_ids:               list of media ids from upload_media()
        :param quote_post_id:           to quote post, put the id here. Requires an Enterprise plan.
        :param poll_options:            list of strings, 2-4 options
        :param poll_duration_minutes:   int, required if poll_options is supplied
        :param reply_settings:          'following' or 'mentionedUsers' to limit who can reply
        :param community_id:            to post to a community, put the id here

        :return: standard response dict, with url and postID added on success
        """

        result = self._call(self.tweepy_api.create_tweet, text=post_text, in_reply_to_tweet_id=reply_to_post_id,
                            media_ids=media_ids, quote_tweet_id=quote_post_id, poll_options=poll_options,
                            poll_duration_minutes=poll_duration_minutes, reply_settings=reply_settings,
                            community_id=community_id)

        if result['error']:
            return result

        post_id = result['twitterResponse'].data['id']
        result['url'] = "https://x.com/" + self.current_handle.replace("@", "") + "/status/" + post_id
        result['postID'] = post_id
        result['tweetID'] = post_id
        result['postHandle'] = self.current_handle
        result['tweetHandle'] = self.current_handle

        return result

    def delete_post(self, post_id):
        """
        Deletes one of your posts.

        Cost: $0.010 per request (Interaction: Delete) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.delete_tweet, post_id)

    def hide_reply(self, post_id):
        """
        Hides a reply to one of your posts.

        Cost: $0.005 per request (Content: Manage) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.hide_reply, post_id, user_auth=True)

    def unhide_reply(self, post_id):
        """
        Unhides a reply to one of your posts.

        Cost: $0.005 per request (Content: Manage) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.unhide_reply, post_id, user_auth=True)

    #######################
    # Posts: read
    def get_post(self, post_id, **params):
        """
        Gets a single post by id.

        Cost: $0.005 per resource (Posts: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_tweet, post_id, user_auth=True, **params)

    def get_posts(self, post_ids, **params):
        """
        Gets up to 100 posts by id.

        Cost: $0.005 per resource (Posts: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_tweets, post_ids, user_auth=True, **params)

    def get_my_posts(self, **params):
        """
        Gets your own timeline of posts.

        Cost: $0.001 per resource (Owned Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_users_tweets, self._get_my_user_id(), user_auth=True, **params)

    def get_user_posts(self, user_id, **params):
        """
        Gets another user's timeline of posts.

        Cost: $0.005 per resource (Posts: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_users_tweets, user_id, user_auth=True, **params)

    def get_my_mentions(self, **params):
        """
        Gets posts mentioning you.

        Cost: $0.001 per resource (Owned Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_users_mentions, self._get_my_user_id(), user_auth=True, **params)

    def get_home_timeline(self, **params):
        """
        Gets your reverse chronological home timeline.

        Cost: $0.005 per resource (Posts: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_home_timeline, user_auth=True, **params)

    def search_recent_posts(self, query, **params):
        """
        Searches posts from the last 7 days.

        Cost: $0.005 per resource (Posts: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.search_recent_tweets, query, user_auth=True, **params)

    def get_recent_post_counts(self, query, **params):
        """
        Gets counts of posts matching a query for the last 7 days. Needs a bearer token in your auth data.

        Cost: $0.005 per request (Counts: Recent) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_recent_tweets_count, query, **params)

    def get_quote_posts(self, post_id, **params):
        """
        Gets posts quoting the given post.

        Cost: $0.005 per resource (Posts: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_quote_tweets, post_id, user_auth=True, **params)

    def get_reposters(self, post_id, **params):
        """
        Gets users who reposted the given post.

        Cost: $0.010 per resource (User: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_retweeters, post_id, user_auth=True, **params)

    def get_liking_users(self, post_id, **params):
        """
        Gets users who liked the given post.

        Cost: $0.010 per resource (User: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_liking_users, post_id, user_auth=True, **params)

    #######################
    # Engagement
    def like_post(self, post_id):
        """
        Likes a post.

        Cost: $0.015 per request (User Interaction: Create) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.like, post_id, user_auth=True)

    def unlike_post(self, post_id):
        """
        Removes a like.

        Cost: $0.010 per request (Interaction: Delete) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.unlike, post_id, user_auth=True)

    def repost(self, post_id):
        """
        Reposts (retweets) a post.

        Cost: $0.015 per request (User Interaction: Create) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.retweet, post_id, user_auth=True)

    def unrepost(self, post_id):
        """
        Removes a repost.

        Cost: $0.010 per request (Interaction: Delete) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.unretweet, post_id, user_auth=True)

    def follow_user(self, user_id):
        """
        Follows a user.

        Cost: $0.015 per request (User Interaction: Create) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.follow_user, user_id, user_auth=True)

    def unfollow_user(self, user_id):
        """
        Unfollows a user.

        Cost: $0.010 per request (Interaction: Delete) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.unfollow_user, user_id, user_auth=True)

    def mute_user(self, user_id):
        """
        Mutes a user.

        Cost: $0.015 per request (User Interaction: Create) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.mute, user_id, user_auth=True)

    def unmute_user(self, user_id):
        """
        Unmutes a user.

        Cost: $0.005 per request (Mute: Delete) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.unmute, user_id, user_auth=True)

    #######################
    # Users
    def get_me(self, **params):
        """
        Gets a variety of information about the current authorized user.

        Cost: $0.010 per resource (User: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_me, user_auth=True, **params)

    def get_user(self, user_id=None, username=None, **params):
        """
        Looks up a user by id or username.

        Cost: $0.010 per resource (User: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_user, id=user_id, username=username, user_auth=True, **params)

    def get_users(self, user_ids=None, usernames=None, **params):
        """
        Looks up to 100 users by id or username.

        Cost: $0.010 per resource (User: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_users, ids=user_ids, usernames=usernames, user_auth=True, **params)

    def get_my_followers(self, **params):
        """
        Gets your followers.

        Cost: $0.001 per resource (Owned Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_users_followers, self._get_my_user_id(), user_auth=True, **params)

    def get_my_following(self, **params):
        """
        Gets the users you follow.

        Cost: $0.001 per resource (Owned Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_users_following, self._get_my_user_id(), user_auth=True, **params)

    def get_user_followers(self, user_id, **params):
        """
        Gets another user's followers.

        Cost: $0.010 per resource (Following/Followers: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_users_followers, user_id, user_auth=True, **params)

    def get_user_following(self, user_id, **params):
        """
        Gets who another user follows.

        Cost: $0.010 per resource (Following/Followers: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_users_following, user_id, user_auth=True, **params)

    def get_my_liked_posts(self, **params):
        """
        Gets posts you have liked.

        Cost: $0.001 per resource (Owned Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_liked_tweets, self._get_my_user_id(), user_auth=True, **params)

    def get_my_muted(self, **params):
        """
        Gets users you have muted.

        Cost: $0.001 per resource (Mute: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_muted, user_auth=True, **params)

    def get_my_blocked(self, **params):
        """
        Gets users you have blocked.

        Cost: $0.001 per resource (Block: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_blocked, user_auth=True, **params)

    #######################
    # Lists
    def create_list(self, name, description=None, private=None):
        """
        Creates a list.

        Cost: $0.010 per request (List: Create) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.create_list, name, description=description, private=private, user_auth=True)

    def update_list(self, list_id, name=None, description=None, private=None):
        """
        Updates a list.

        Cost: $0.005 per request (List: Manage) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.update_list, list_id, name=name, description=description, private=private,
                          user_auth=True)

    def delete_list(self, list_id):
        """
        Deletes a list.

        Cost: $0.005 per request (List: Manage) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.delete_list, list_id, user_auth=True)

    def add_list_member(self, list_id, user_id):
        """
        Adds a user to a list.

        Cost: $0.005 per request (List: Manage) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.add_list_member, list_id, user_id, user_auth=True)

    def remove_list_member(self, list_id, user_id):
        """
        Removes a user from a list.

        Cost: $0.005 per request (List: Manage) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.remove_list_member, list_id, user_id, user_auth=True)

    def get_list(self, list_id, **params):
        """
        Gets a list by id.

        Cost: $0.005 per resource (List: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_list, list_id, user_auth=True, **params)

    def get_list_posts(self, list_id, **params):
        """
        Gets posts from a list.

        Cost: $0.005 per resource (Posts: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_list_tweets, list_id, user_auth=True, **params)

    def get_my_lists(self, **params):
        """
        Gets lists you own.

        Cost: $0.001 per resource (Owned Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_owned_lists, self._get_my_user_id(), user_auth=True, **params)

    #######################
    # Direct messages
    def send_dm(self, participant_id, text, media_id=None):
        """
        Sends a dm to a user, creating the conversation if needed.

        Cost: $0.015 per request (DM Interaction: Create) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.create_direct_message, participant_id=participant_id, text=text,
                          media_id=media_id, user_auth=True)

    def get_dm_events(self, **params):
        """
        Gets your dm events.

        Cost: $0.010 per resource (DM Event: Read) https://docs.x.com/x-api/getting-started/pricing
        """
        return self._call(self.tweepy_api.get_direct_message_events, user_auth=True, **params)

    #######################
    # Media
    def upload_media(self, file_path, media_category='tweet_image'):
        """
        Uploads a file with the v2 chunked flow and returns a media id for use in create_post().
        https://docs.x.com/x-api/media/media-upload-initialize

        Tweepy has no v2 media support, so this is a direct call. X documents these endpoints for OAuth 2.0 with the
        media.write scope, so OAuth 1.0a may return a 403 here.

        Cost: $0.005 per request (Media Metadata) https://docs.x.com/x-api/getting-started/pricing

        :param file_path:           path to the file to upload
        :param media_category:      tweet_image, tweet_video, tweet_gif, dm_image, dm_video, dm_gif, subtitles

        :return: standard response dict, with mediaID added on success
        """

        base_url = "https://api.x.com/2/media/upload"
        chunk_size = 4 * 1024 * 1024

        try:
            total_bytes = os.path.getsize(file_path)
            media_type = mimetypes.guess_type(file_path)[0]
            session = self._get_oauth_session()

            init = session.post(f"{base_url}/initialize",
                                json={"media_type": media_type, "total_bytes": total_bytes,
                                      "media_category": media_category})
            init.raise_for_status()
            media_id = init.json()['data']['id']

            with open(file_path, 'rb') as f:
                segment_index = 0
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    append = session.post(f"{base_url}/{media_id}/append",
                                          data={"segment_index": segment_index},
                                          files={"media": chunk})
                    append.raise_for_status()
                    segment_index = segment_index + 1

            finalize = session.post(f"{base_url}/{media_id}/finalize")
            finalize.raise_for_status()
        except Exception as e:
            function_defined_error_message = "Failed while trying to upload media. self.upload_media"
            print(function_defined_error_message)
            print(e)

            return {"error": True,
                    "twitterResponse": None,
                    "errorData": {"functionError": function_defined_error_message,
                                  "tweepyError": str(e)}}

        return {"error": False,
                "twitterResponse": finalize.json(),
                "errorData": None,
                "mediaID": media_id}

    #######################
    # Backwards compatibility
    def create_tweet(self, tweet_message_str, reply_to_tweet_id=None, image_data=None, quote_tweet_id=None):
        """
        Deprecated, use create_post(). image_data must now be a file path, as media goes through v2 upload.
        """
        media_ids = None
        if image_data is not None:
            image_data = image_data if type(image_data) is list else [image_data]
            media_ids = []
            for image in image_data:
                upload = self.upload_media(image)
                if upload['error']:
                    return upload
                media_ids.append(upload['mediaID'])

        return self.create_post(tweet_message_str, reply_to_post_id=reply_to_tweet_id, media_ids=media_ids,
                                quote_post_id=quote_tweet_id)

    def delete_tweet(self, tweet_id):
        """
        Deprecated, use delete_post().
        """
        return self.delete_post(tweet_id)

    def get_my_user_info(self):
        """
        Deprecated, use get_me().
        """
        return self.get_me()
