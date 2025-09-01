from typing import Optional
from lukhed_basic_utils.githubCommon import KeyManager
from lukhed_basic_utils import osCommon as osC
import tweepy

# https://docs.tweepy.org/en/v3.10.0/api.html
# https://developer.twitter.com/en/docs/twitter-api/v1/rate-limits



class X():
    def __init__(self, handle, key_management='github', x_api_setup=False):
        """
        This class is a custom tweepy wrapper for posting on X (formerly Twitter). It includes key management and 
        basic endpoints.

        Parameters
        ----------
        handle : str
            The Twitter handle to use for API requests.
        key_management : str, optional
            The strategy key management strategy to use. Options are:
            'local' - stores/retrieve your api key on your local hard drive (working directory)
            'github' - stores/retrieves your api key in a private repo (helpful to allow access across different hardware)
            Default is 'github'.
        x_api_setup : bool, optional
            Set this to true for initial setup of the X API credentials. You will be prompted to enter your 
            API information from https://developer.x.com/en.
         """

        # class variables
        osC.check_create_dir_structure(['lukhedConfig'])
        self.key_management = key_management.lower()
        self._token_file_path = osC.create_file_path_string(['lukhedConfig', 'localTokenFile.json'])
        self.current_handle = handle
        self._parse_handle()
        self._key_data = {}
        self._project_name = 'xapi' # used for key management, should be unique to repo and lowercase.
        self.current_version = 2

        # Objects used
        self.tweepy_api: Optional[tweepy.Client] = None
        self._kM: Optional[KeyManager] = None

        # One time setup option
        if x_api_setup:
            self._x_api_setup()

        # Load access data
        self._check_create_km()

        self._tweepy_generate_api(self.current_version)
    
    def _x_api_setup(self):
        print("This is the lukhed setup for the X API. If you haven't already, you first need to setup an"
              " X api developer acccount (free here: https://developer.x.com/en). To continue, you need the following"
              " from the setup:\n"
              "1. Access Token\n"
              "2. Access Token Secret\n"
              "3. Api Key\n"
              "4. Api Secret\n"
              "If you don't know how to get these, you can find instructions here:\n"
              "https://docs.x.com/x-api/getting-started/getting-access")
        
        if input("\n\nAre you ready to continue (y/n)?") == 'n':
            print("OK, come back when you have setup your developer account")
            quit()

        access_token = input("Paste your access token then press enter:\n").replace(" ", "")
        access_token_secret = input("Paste your access token secret then press enter:\n").replace(" ", "")
        api_key = input("Paste your API key here:\n").replace(" ", "")
        api_secret = input("Paste your API secret here:\n").replace(" ", "")

        self._key_data[self.current_handle] = dict()
        self._key_data[self.current_handle]['accessToken'] = access_token
        self._key_data[self.current_handle]['accessTokenSecret'] = access_token_secret
        self._key_data[self.current_handle]['apiKey'] = api_key
        self._key_data[self.current_handle]['apiSecret'] = api_secret

        print("\n\nThe X portion is complete! Now setting up key management with lukhed library...")
        self._kM = KeyManager(self._project_name, config_file_preference=self.key_management, 
                             provide_key_data=self._key_data)

    def _check_create_km(self):
        if self._kM is None:
            # get the key data previously setup
            self._kM = KeyManager(self._project_name, config_file_preference=self.key_management)
            self._key_data = self._kM.key_data
    
    def _parse_handle(self):
        # accept a handle with or without the @symbol
        if "@" not in self.current_handle:
            self.current_handle = "@" + self.current_handle

    def _tweepy_generate_api(self, version):
        self.current_version = version
        key_data = self._key_data[self.current_handle]
        if version == 2:
            """
            https://docs.tweepy.org/en/stable/authentication.html#id3
            need user context to unlock all methods
            """
            return tweepy.Client(consumer_key=key_data["apiKey"],
                                 consumer_secret=key_data["apiSecret"],
                                 access_token=key_data["accessToken"],
                                 access_token_secret=key_data["accessTokenSecret"])
        elif version == 1:
            auth = tweepy.OAuthHandler(key_data['apiKey'], key_data['apiSecret'])
            auth.set_access_token(key_data['accessToken'], key_data['accessTokenSecret'])

            return tweepy.API(auth)
        else:
            return None

    def _check_create_tweepy_api(self, version_int):
        """
        This function creates the tweepy api based on the twitter API version requested.
        The free twitter API currently supports v2 endpoints but allows access to some v1 endpoints still

        :param version_int:     int(), 1 or 2
        :return:
        """
        # Create a twitter API if one does not exist or if the current api version is not correct for the method
        if self.tweepy_api is None or version_int != self.current_version:
            self.tweepy_api = self._tweepy_generate_api(version_int)

    def _try_print_tweepy_exception(self, tweepy_exception):
        """
        :param tweepy_exception:
        :return:
        """
        print("Trying to print exception:")

        try:
            print(tweepy_exception)
            tweepy_defined_error_message = tweepy_exception
        except:
            tweepy_defined_error_message = "failed getting the tweepy defined error message"
            print(tweepy_defined_error_message)

        return tweepy_defined_error_message

    def _parse_image_data(self, image_data):
        media_ids = []
        if type(image_data) is list:
            for i in image_data:
                media = self.tweepy_api.media_upload(i)
                media_ids.append(media.media_id)
        else:
            media = self.tweepy_api.media_upload(image_data)
            media_ids.append(media.media_id)

        return media_ids

    #######################
    # Free with API
    def create_tweet(self, tweet_message_str, reply_to_tweet_id=None, image_data=None, quote_tweet_id=None):
        """
        This function creates a tweet. It uses v2 twitter endpoints and comes with the Basic (free) plan. All accounts
        can use this functionality.

        Tweepy doc is here:
        https://docs.tweepy.org/en/stable/client.html#tweepy.Client.create_tweet


        :param tweet_message_str:           text you want to tweet

        :param reply_to_tweet_id:           tweet ID you want to reply to. Note: if this is supplied,
                                            @[handle_replying_to] must be in tweet text for it to show up in the
                                            replies

        :param image_data:                  list or image. Image can be path to image or actual image

        :param quote_tweet_id:              to quote tweet, put the id here

        :return: success bool and tweepy response if applicable
        """

        try:
            if image_data is not None:
                self._check_create_tweepy_api(1)
                media_ids = self._parse_image_data(image_data)
            else:
                media_ids = None

            self._check_create_tweepy_api(2)
            status_update = self.tweepy_api.create_tweet(text=tweet_message_str, in_reply_to_tweet_id=reply_to_tweet_id,
                                                  media_ids=media_ids, quote_tweet_id=quote_tweet_id)

            tweet_url = "https://twitter.com/" + self.current_handle.replace("@", "") + "/status/" + \
                        status_update.data['id']
            tweet_id = status_update.data['id']
        except Exception as e:
            function_defined_error_message = "Failed while trying to tweet. self.tweepy_api.create_tweet"
            print(function_defined_error_message)

            tweepy_defined_error_message = self._try_print_tweepy_exception(e)

            return {"error": True,
                    "twitterResponse": None,
                    "errorData": {"functionError": function_defined_error_message,
                                  "tweepyError": tweepy_defined_error_message}}

        return {"error": False,
                "twitterResponse": status_update,
                "errorData": None,
                "url": tweet_url,
                "tweetID": tweet_id,
                "tweetHandle": self.current_handle}

    def delete_tweet(self, tweet_id):
        """
        This function deletes a tweet. It uses v2 twitter endpoints and comes with the Basic (free) plan. All accounts
        can use this functionality.

        Tweepy doc is here:
        https://docs.tweepy.org/en/stable/client.html#tweepy.Client.delete_tweet

        :param tweet_id:
        :return:
        """

        self._check_create_tweepy_api(2)
        try:
            twitter_response = self.tweepy_api.delete_tweet(tweet_id)
        except Exception as e:
            function_defined_error_message = "Failed while trying to delete tweet. self.tweepy_api.delete_tweet"
            print(function_defined_error_message)
            tweepy_defined_error_message = self._try_print_tweepy_exception(e)

            return {"error": True,
                    "twitterResponse": None,
                    "errorData": {"functionError": function_defined_error_message,
                                  "tweepyError": tweepy_defined_error_message}}

        return {"error": False,
                "twitterResponse": twitter_response,
                "errorData": None}

    def get_my_user_info(self):
        """
        This function gets a variety of information about the current authorized user.
        It uses v2 twitter endpoints and comes with the Basic (free) plan. All accounts can use this functionality.

        Tweepy doc is here:
        https://docs.tweepy.org/en/stable/client.html#tweepy.Client.get_me

        :return:
        """

        self._check_create_tweepy_api(2)
        try:
            twitter_response = self.tweepy_api.get_me()
        except Exception as e:
            function_defined_error_message = "Failed while trying lookup user. self.tweepy_api.get_user"
            print(function_defined_error_message)
            tweepy_defined_error_message = self._try_print_tweepy_exception(e)

            return {"error": True,
                    "twitterResponse": None,
                    "errorData": {"functionError": function_defined_error_message,
                                  "tweepyError": tweepy_defined_error_message}}

        return {"error": False,
                "twitterResponse": twitter_response,
                "errorData": None}
