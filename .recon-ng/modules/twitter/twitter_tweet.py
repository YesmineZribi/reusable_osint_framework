# module required for framework integration
from recon.core.module import BaseModule
# mixins for desired functionality
# module specific imports
import tweepy
import os, sys
import json
import time
from datetime import datetime

class Module(BaseModule):

    # modules are defined and configured by the "meta" class variable
    # "meta" is a dictionary that contains information about the module, ranging from basic information, to input that affects how the module functions
    # below is an example "meta" declaration that contains all of the possible definitions

    meta = {
        'name': 'Twitter tweets Recon',
        'author': 'Yesmine Zribi',
        'version': '1.0',
        'description': 'Collect recon about a about tweets: search tweets based on search query, location, etc., get retweeters/retweets',
        'dependencies': ['tweepy'],
        'required_keys': ['twitter_api', 'twitter_secret'],
        'comments': (
            'Add any user you want to run recon on in the profiles table through the db insert profiles command',
            'Location filtering is taken from the Geotagging API, but will fall back to user\'s Twitter profile',
            'For geolocation: You cannot use the near operator via the API to geocode arbitrary locations; however you can use this geocode parameter to search near geocodes directly. A maximum of 1,000 distinct “sub-regions” will be considered when using the radius modifier.',

        ),
        'options': (
            ('tweet_id', '', False, 'Set to the tweet id from which you want to collect recon'),
            ('tweet_ids','',False, 'Set to a list of comma-separated tweets ids to lookup ex:123,123,123'),
            ('get_status',False, False, 'Set to true to return get the status with the defined tweet_id'),
            ('statuses_lookup', False, False, 'Set to true to enable bulk lookup of tweets and add list the ids in tweet_ids'),
            ('search_for_tweets', False, False, 'Set to true to enable searching for tweets based on search parameters'),
            ('get_retweets',False, False, 'Set to true to get retweets of the tweet with the specified tweet_id'),
            ('get_retweeters',False, False, 'Set to true to get user info of users who retweeted the tweet with the specified tweet_id'),
            ('sleep_time', 2, False, 'Set how much time to sleep if rate limit is reached, default is 2 minutes, max is 15'),
        ),
    }

    # "name", "author", "version", and "description" are required entries
    # "dependencies" is required if the module requires the installation of a third party library (list of PyPI install names)
    # "files" is required if the module includes a reference to a data file in the "/data" folder of the marketplace repository
    # "required_keys" is required if the module leverages an API or builtin functionality that requires a key
    # "query" is optional and determines the "default" source of input
    # the "SOURCE" option is only available if "query" is defined
    # "options" expects a tuple of tuples containing 4 elements:
    # 1. the name of the option
    # 2. the default value of the option (strings, integers and boolean values are allowed)
    # 3. a boolean value (True or False) for whether or not the option is mandatory
    # 4. a description of the option
    # "comments" are completely optional

    # optional method
    def module_pre(self):
        # Authentication
        auth = tweepy.AppAuthHandler(self.get_key('twitter_api'), self.get_key('twitter_secret'))
        self.api = tweepy.API(auth)

        #Build result directory structure
        root_path = os.path.dirname(os.path.abspath(sys.path[0])) #Get the root directory
        self.twitter_recon_path = os.path.join(root_path,'twitter_recon') #directory to store collected data
        if not os.path.exists(self.twitter_recon_path):
            os.makedirs(self.twitter_recon_path,mode=0o777)
        self.tweets_path = os.path.join(self.twitter_recon_path, 'tweets') #directory to store data collected about twitter users
        if not os.path.exists(self.tweets_path):
            os.makedirs(self.tweets_path,mode=0o777)

        #Check if tweetid is valid
        if self.options['tweet_id'] and not(isinstance(self.options['tweet_id'],int)):
            self.error("Illegal type for tweet_id, need to be set to an int (ex:12345)")

        #Check if it is a comma-separated list + check if ids are valid numerics
        if self.options['tweet_ids'] and not(all(x.isnumeric() for x in self.options['tweet_ids'].split(","))):
            self.error("Some elements in tweet_ids are not valid, make sure it is a list of integers")

        #Check that get_status was not enabled without setting a tweet_id
        if (self.options['get_status'] or self.options['get_retweets'] or self.options['get_retweeters']) and not self.options['tweet_id']:
            self.error('get_status or get_retweets or get_retweeters was enabled but no tweet_id was provided')

        #Check that statuses_lookup was not enabled without a list of tweets
        if (self.options['statuses_lookup'] and not self.options['tweet_ids']):
            self.error("statuses_lookup was enabled but no tweet id list was provided, either disable statuses_lookup or set tweet_ids to a list of tweet ids")


    # mandatory method
    # the second parameter is required to capture the result of the "SOURCE" option, which means that it is only required if "query" is defined within "meta"
    # the third parameter is required if a value is returned from the "module_pre" method
    def module_run(self):
        for key in ['get_status','statuses_lookup','search_for_tweets','get_retweets','get_retweeters']:
            if self.options[key]:
                method_to_call = getattr(self,key)
                method_to_call()

    # optional method
    # the first received parameter is required to capture an item from the queue
    # all other parameters passed in to "self.thread" must be accounted for
    def module_thread(self, host, url, headers):
        # never catch KeyboardInterrupt exceptions in the "module_thread" method as threads don't see them
        # do something leveraging the api methods discussed below
        pass

# -- Helper methods
    def get_status(self):
        #Create tweet_id directory if it does not already exist
        id_str = str(self.options['tweet_id'])
        tweet_path = os.path.join(self.tweets_path,f'tweet_{id_str}')
        if not os.path.exists(tweet_path):
            os.makedirs(tweet_path,mode=0o777)

        self.verbose(f'Getting status with id: {id_str}')
        #Ask user to use default settings or customize input
        user = input("Use default settings (y/n)?: ")
        default = True #Flag variable
        if user.lower() in "no":
            default = False
            #Get user to configure result options
            trim_user = input("trim user: set to True if you want user ID to be provided instead of user objects: ")
            if trim_user.lower() in 'true':
                trim_user = True
            else:
                trim_user = False

            include_entities = input("include entities: set to True if you want entities node to be included: ")
            if include_entities.lower() in 'true':
                include_entities = True
            else:
                include_entities = False

            include_ext_alt_text = input("include ext alt text: set to True to inlude alt text if it has been added to any attached media entites: ")
            if include_ext_alt_text.lower() in 'true':
                include_ext_alt_text = True
            else:
                include_ext_alt_text = False

            include_card_uri = input("Set to true if the retrieved Tweet should include a card_uri attribute when there is an ads card attached to the Tweet and when that card was attached using the card_uri value: ")
            if include_card_uri.lower() in 'true':
                include_card_uri = True
            else:
                include_card_uri = False

        try:
            result = ''
            #Fetch results from API
            if default:
                result = self.api.get_status(id=self.options['tweet_id'])
            else:
                result = self.api.get_status(id=self.options['tweet_id'],trim_user=trim_user,include_entities=include_entities,include_ext_alt_text=include_ext_alt_text,
                include_card_uri=include_card_uri)

            #Create file to store results
            now = datetime.now()
            dt_string = now.strftime("%d_%m_%y_%H_%M_%S")
            tweet_info_file = os.path.join(tweet_path,f'status_{id_str}_{dt_string}.json')
            with open(tweet_info_file, 'w') as file:
                file.write(json.dumps(result._json, indent=3, sort_keys=True)) #Dump results in the file

        except tweepy.TweepError:
            print(tweepy.tweet_path.reponse.text)



    def statuses_lookup(self):
        #Format tweet_ids list for input
        tweet_ids = []
        for tweet_id in self.options['tweet_ids'].split(","):
            tweet_ids.append(int(tweet_id))
        #Create tweet_id directory if it does not already exist

        statuses_lookup_path = os.path.join(self.tweets_path,f'statuses_lookup')
        if not os.path.exists(statuses_lookup_path):
            os.makedirs(statuses_lookup_path,mode=0o777)

        #Ask user to use default settings or customize input
        user = input("Use default settings (y/n)?: ")
        default = True #Flag variable
        if user.lower() in "no":
            default = False
            #Get user to configure result options
            trim_user = input("trim user: set to True if you want user ID to be provided instead of user objects: ")
            if trim_user.lower() in 'true':
                trim_user = True
            else:
                trim_user = False

            include_entities = input("include entities: set to True if you want entities node to be included: ")
            if include_entities.lower() in 'true':
                include_entities = True
            else:
                include_entities = False

            include_ext_alt_text = input("include ext alt text: set to True to inlude alt text if it has been added to any attached media entites: ")
            if include_ext_alt_text.lower() in 'true':
                include_ext_alt_text = True
            else:
                include_ext_alt_text = False

            include_card_uri = input("include card ui: Set to True if the retrieved Tweet should include a card_uri attribute when there is an ads card attached to the Tweet and when that card was attached using the card_uri value: ")
            if include_card_uri.lower() in 'true':
                include_card_uri = True
            else:
                include_card_uri = False
            map_ = input("map: Set to True to include tweets that cannot be shown. Defaults to False: ")
            if map_.lower() in 'true':
                map_ = True
            else:
                map_ = False
        #Ask user if they want result dumped in one files or multiple
        same_file = input("Would you like all statuses to be put in the same file (y/n)?: ")
        if same_file.lower() in "yes":
            same_file = True
        else:
            same_file = False

        self.verbose(f'Performing statuses lookup')
        try:
            result = ''
            if default:
                result = self.api.statuses_lookup(tweet_ids)
            else:
                result = self.api.statuses_lookup(tweet_ids, include_entities=include_entities, trim_user=trim_user, map_=map_, include_ext_alt_text=include_ext_alt_text,
                include_card_uri=include_card_uri)

            now = datetime.now()
            dt_string = now.strftime("%d_%m_%y_%H_%M_%S")
            if same_file:
                #Create file to store results
                tweets_info_file = os.path.join(statuses_lookup_path,f'statuses_{dt_string}.json')
                #Put all tweets in a list
                tweets = []
                for status in result:
                    tweets.append(status._json)

                with open(tweets_info_file, 'w') as file:
                        file.write(json.dumps(tweets, indent=3, sort_keys=True)) #Dump results in the file
            else: #Create a file and dump result for each tweet
                for status in result:
                    tweet_id_str = str((status._json)['id'])
                    self.verbose(f"Fetching tweet with id {tweet_id_str}")
                    tweet_info_file = os.path.join(statuses_lookup_path,f'status_{tweet_id_str}_{dt_string}.json')
                    with open(tweet_info_file, 'w') as file:
                        file.write(json.dumps(status._json, indent=3, sort_keys=True)) #Dump results in the file


        except tweepy.TweepError:
            print(tweepy.tweet_path.reponse.text)


    def convert_to_float(self,value):
        valid = False
        value_f = 0.0
        while(not(valid)):
            try:
                value_f = float(value)
                valid = True
            except ValueError:
                self.print_exception('The provided value is invalid')
                value = input("Please enter a valid float value: ")
        return value_f

    def convert_to_int(self, value):
        valid = False
        value_i = 0
        while(not(valid)):
            try:
                value_i = int(value)
                valid = True
            except ValueError:
                self.print_exception("The provided value is invalid")
                value = input("Please enter a valid int value: ")
        return value_i

    def search_for_tweets(self):
        #Create directory if it does not exist
        search_result_path = os.path.join(self.tweets_path,f'search_results')
        if not os.path.exists(search_result_path):
            os.makedirs(search_result_path,mode=0o777)

        #Ask user for search query
        search_query = input("Enter the search query (500 characters max including operators): ")
        #Ask for geocode
        print("Enter the geocode to return tweets by users located within a given radius of the given latitude/longitude.")
        latitude = input("latitude: ")
        latitude = self.convert_to_float(latitude) if latitude else None

        longitude = input("longitude: ")
        longitude = self.convert_to_float(longitude) if longitude else None

        radius = input("radius: ")
        radius = self.convert_to_float(radius) if radius else None

        unit = input("km or mi? ")
        if unit:
            while(unit not in ["km","mi"]):
                unit = input("Invalid unit please enter km or mi: ")
        else:
            unit = None
        geocode = f"{latitude},{longitude},{radius}{unit}" if (latitude and longitude and radius) else None
        #Ask for language
        lang = input("Restrict tweets to the given language, given by an ISO 639-1 code: ")
        lang = lang if lang else None
        #Ask for result type
        result_type = input("What type of results would you prefer to receive (mixed/recent/popular)? If you want to learn more about result types, enter \"?\": ")
        if result_type:
            while(result_type not in ["mixed", "recent", "popular"]):
                result_type = input("What type of results would you prefer to receive (mixed/recent/popular)? If you want to learn more about result types, enter \"?\": ")
                if result_type in "?":
                    self.output("mixed : include both popular and real time results in the response")
                    self.output("recent : return only the most recent results in the response")
                    self.output("popular : return only the most popular results in the response")
        else:
            result_type = "mixed" #default value

        #Ask for count
        count = input("Set the number of results to try and retrieve per page: ")
        if count:
            count = self.convert_to_int(count)
        else:
            count = 200 #Set default if not specified
        #Ask for date limit
        until = input("Set this to return the tweets created before the given date Note: search index has a 7-day limit. In other words, no tweets will be found for a date older than one week (input format: YYYY-MM-DD): ")
        until = until if until else None
        #Ask for since_id
        since_id = input("Set this to return statuses with an ID greater than (that is, more recent than) the specified ID: ")
        since_id = self.convert_to_int(since_id) if since_id else None
        #Ask for max_id
        max_id = input("Set this to return only statuses with an ID less than (that is, older than) or equal to the specified ID: ")
        max_id = self.convert_to_int(max_id) if max_id else None
        #Ask for include_entities
        include_entities = input("Set to False to not include entities node. Defaults to True: ")
        if include_entities and include_entities.lower() in "false":
            include_entities = False
        else:
            include_entities = True

        try:
            #Accumulate result in a list
            tweets_returned = []
            for status in self.limit_handled(tweepy.Cursor(self.api.search, q=search_query,geocode=geocode,lang=lang,result_type=result_type,count=count,until=until,since_id=since_id,
            max_id=max_id,include_entities=include_entities).items()):
                tweets_returned.append(status._json)

            #Write results to a json file
            now = datetime.now()
            dt_string = now.strftime("%d_%m_%y_%H_%M_%S")
            search_result_file = os.path.join(search_result_path,f"search_result_{dt_string}.json")
            with open(search_result_file, 'w') as file:
                file.write(json.dumps(tweets_returned, indent=3, sort_keys=True)) #Dump results in the file

        except tweepy.TweepError:
            print(tweepy.tweet_path.reponse.text)


    def get_retweeters(self):
        #Create tweet_id directory if it does not already exist
        id_str = str(self.options['tweet_id'])
        tweet_path = os.path.join(self.tweets_path,f'tweet_{id_str}')
        if not os.path.exists(tweet_path):
            os.makedirs(tweet_path,mode=0o777)

        self.verbose(f'Getting retweeters of tweet with id: {id_str} (only up to 100 returned)')
        try:
            returned_ids = self.api.retweeters(id=self.options['tweet_id'],stringify_ids=True)
            #create json file to dump ids
            now = datetime.now()
            dt_string = now.strftime("%d_%m_%y_%H_%M_%S")
            retweeters_file = os.path.join(tweet_path,f'retweeters_of_{id_str}_{dt_string}.json')
            with open(retweeters_file,'w') as file:
                for id in returned_ids:
                    file.write("%s\n" % id)
        except tweepy.TweepError:
            print(tweepy.tweet_path.reponse.text)

    def get_retweets(self):
        id_str = str(self.options['tweet_id'])
        #Create tweet_id directory if it does not already exist
        id_str = str(self.options['tweet_id'])
        tweet_path = os.path.join(self.tweets_path,f'tweet_{id_str}')
        if not os.path.exists(tweet_path):
            os.makedirs(tweet_path,mode=0o777)

        #Ask user for default/custom input
        #Ask user to use default settings or customize input
        user = input("Use default settings (y/n)?: ")
        default = True #Flag variable
        if user.lower() in "no":
            default = False
            #Get user to configure result options
            #Ask user for count and check it is valid
            valid = False
            count = 0
            while(not(valid)):
                try:
                    count = int(input("Set the number of retweets to retrieve (up to 100): "))
                    if (count >= 0 and count <= 100):
                        valid = True
                    else:
                        raise ValueError
                except ValueError:
                    self.print_exception('The provided count value is invalid, please enter an integer between 0 and 100')

        #Ask user if they want result dumped in one files or multiple
        same_file = input("Would you like all statuses to be put in the same file (y/n)?: ")
        if same_file.lower() in "yes":
            same_file = True
        else:
            same_file = False

        try:
            if default:
                count = 100

            #Get the retweets
            result = self.api.retweets(id = self.options['tweet_id'], count=count)

            now = datetime.now()
            dt_string = now.strftime("%d_%m_%y_%H_%M_%S")
            if same_file:
                #Create file for retweets
                retweets_file = os.path.join(tweet_path,f'retweets_of_{id_str}_{dt_string}.json')

            retweets = []
            for status in result: #Put the statuses in a list
                retweets.append(status._json)

            if same_file:
                with open(retweets_file, 'w') as file:
                    file.write(json.dumps(retweets, indent=3, sort_keys=True))
            else:
                retweet_id_str = ''
                for status in retweets:
                    retweet_id_str = status['id']
                    self.verbose("Fetching retweet with id {retweet_id_str}")
                    retweet_info_file = os.path.join(tweet_path,f'retweet_{retweet_id_str}_{dt_string}.json')
                    with open(retweet_info_file, 'w') as file:
                        file.write(json.dumps(status, indent=3, sort_keys=True)) #Dump results in the file

        except tweepy.TweepError:
            print(tweepy.tweet_path.reponse.text)

    def limit_handled(self,cursor):
        while True:
            try:
                yield cursor.next()
            except tweepy.RateLimitError:
                self.alert(f'Rate limit reached, sleeping for {sleep_time} minutes') #report limit reached
                time.sleep(self.options['sleep_time'] * 60)
            except StopIteration:
                return
