# module required for framework integration and all social network modules
from recon.mixins.social_module import *
# mixins for desired functionality
# module specific imports
import tweepy
import os, sys
import json
import time
from datetime import datetime
import traceback

class Module(SocialModule):

    # modules are defined and configured by the "meta" class variable
    # "meta" is a dictionary that contains information about the module, ranging from basic information, to input that affects how the module functions
    # below is an example "meta" declaration that contains all of the possible definitions

    meta = {
        'name': 'twitter_user_recon',
        'author': SocialModule.meta['author'],
        'version': SocialModule.meta['version'],
        'description': 'Collect recon about a twitter user: their information, followers, friends, or timeline',
        'dependencies': ['tweepy'],
        'required_keys': ['twitter_api', 'twitter_secret'],
        'comments': (
            'Add any user you want to run recon on in the profiles table through the db insert profiles command',
            'Set usource type to user_id to run the source(s) as a user_id. Recommended if need to disambiguate when a valid user ID is also a valid screen name.',
            'Set source type to screen_name to run the source(s) as a screen_name. Recommended if need to disambiguate when a valid user ID is also a valid screen name.',
            'Set source type to id to run as either (user_id/screen_name)',
            'Can only fetch the 20 most recent statuses of a user',
            'Twitter limits api calls to 15/15 min window',

        ),
        'options': SocialModule.meta['options'] + (
            ('user_info', True, False, 'Set to true to enable collection of user account info'),
            ('user_followers', False, False, 'Set to true to enable collection of user followers'),
            ('user_friends', False, False, 'Set to true to enable collection of user friends'),
            ('user_timeline', False, False, 'Set to true to enable collection of user timeline'),
            ('user_favorites', False, False, 'Set to true to enable collection of user\'s liked posts'),
            ('users_lookup', False, False, 'Set to true to enable lookup of up to 100 users'),
            ('enable_fetch_all', False, False, 'Set to true to enable bulk account fetching (required to use analysis module)'),
            ('cursor', -1, False, 'Breaks result into pages, -1 to start from first page'),
            ('count', 200, False, 'The number of results to try and retrive per page. Default is 200 (not applicable to user info)'),
            ('skip_status', True, False, 'Boolean indicating whether statuses will not be included in the returned objects. Default to true'),
            ('include_user_entities', True, False, 'User object entities node will not be included when set to false. Defaults to true'),
        ),
    }

    def module_pre(self):
        super().module_pre()
        # Authentication
        auth = tweepy.AppAuthHandler(self.get_key('twitter_api'), self.get_key('twitter_secret'))
        self.api = tweepy.API(auth)

        #Check if cursor and counts are ints
        for key in ['cursor','count']:
            if not(isinstance(self.options[key],int)):
                self.error(f'Illegal value for {key} (ints only)')

        #If multiple users disable fecth_user_info in favor and enable fetch_users_lookup to save API calls
        if not(isinstance(self.options['source'],int)) and (len(self.options['source'].split(",")) > 1):
            if self.options['user_info']:
                self.alert("Multiple users provided disabling user_info in favor of users_lookup")
                self.options['user_info'] = False
                self.options['users_lookup'] = True


        self.recon_functions = ['users_lookup', 'user_info', 'user_friends', 'user_followers', 'user_timeline', 'user_favorites'] #Store for future use

        #if enable_fetch_all is set to true, enable all functions
        if self.options['enable_fetch_all']:
            for key in self.recon_functions:
                self.options[key] = True

        #If user_favorites is enabled and source is not ids (will need to get the ids given the screen_name)
        if self.options['user_favorites'] and not(all(x.isnumeric() for x in self.handles)):
            if len(self.handles) > 1: #enable users_lookup if more than one handle
                self.alert("user_favorites requires user ids, users_lookup enabled")
                self.options['users_lookup'] = True if not(self.options['users_lookup']) else self.options['users_lookup']
                self.options['user_info'] = False
            else: #enable user_info if only one handle
                self.alert("user_favorites requires user ids, user_info enabled")
                self.options['user_info'] = True if not(self.options['user_info']) else self.options['user_info']
                self.options['users_lookup'] = False

        if self.options['users_lookup'] and all(x.isnumeric() for x in self.handles): #users_lookup api calls taks user_idS or screen_nameS as parameter
            self.alert("users_lookup enabled temporarly setting source_type to user_ids")
            self.options['source_type'] = 'user_ids'
        elif self.options['users_lookup'] and all(isinstance(x,str) for x in self.handles):
            self.alert("users_lookup enabled temporarly setting source_type to screen_names")
            self.options['source_type'] = 'screen_names'

        self.timeline_path = '' #Keep track of whether fetch_timeline was called


    def module_run(self):
        super().module_run()
        if not self.options['analysis_recon']:
            # handles = self.options['source'].split(",")
            self.verbose("---Starting module---")
            if self.options['users_lookup']:
                self.fetch_users_lookup()

            for handle in self.handles:
                #Get the user path
                user_path = self.user_path[handle]
                #fetch info enabled by user
                for key in self.recon_functions[1:]: #exclude users_lookup
                    if self.options[key]:
                        fetch_to_call = getattr(self, f'fetch_{key}')
                        fetch_to_call(handle,user_path) #Call the right method based on the options set by the user

# -- Implementation of the abstract helper methods --
    def fetch_user_info(self,username, user_path):
        try:
            #Fetch the info using the api
            results = self.api.get_user(**{self.options['source_type']:username})
            #Create the file in which to dump the results
            now = datetime.now()
            dt_string = now.strftime("%d_%m_%y_%H_%M_%S")
            user_info_file = os.path.join(user_path,f'info_{dt_string}.json')
            self.verbose(f"Retrieving info for {username}...")
            with open(user_info_file,'w') as file:
                file.write(json.dumps(results._json, indent=3, sort_keys=True)) #write the json result in a file

        except tweepy.TweepError as e:
            if(e.api_code == 429):
                sleep_time = str(self.options['sleep_time'])
                self.alert(f'Rate limit reached, sleeping for {sleep_time} minutes') #report limit reached
                time.sleep(self.options['sleep_time'] * 60)
            else:
                print(e.reason)

        return user_info_file


    def fetch_users_lookup(self):
        paths = {}
        for handle in self.handles:
            #Create their respective directories
            user_path = os.path.join(self.users_path, f'{str(handle)}')
            if not os.path.exists(user_path):
                os.makedirs(user_path,mode=0o777)
            #Create the user info file
            now = datetime.now()
            dt_string = now.strftime("%d_%m_%y_%H_%M_%S")
            user_info_file = os.path.join(user_path,f'info_{dt_string}.json')
            paths[handle] = user_info_file #store it for later reference

        try:
            self.output("Performing users lookup for given handles...")
            #Fetch users' info using the api
            results = self.api.lookup_users(**{self.options['source_type']:self.handles})
            result_file = ''
            username = ''
            user_files = []
            for user in results:
                #Get the right file
                if self.options['source_type'] == 'screen_names':
                    username = user._json['screen_name']
                    result_file = paths[username]
                else:
                    username = user._json['id']
                    result_file = paths[username]
                #Dump result in it
                with open(result_file, 'w') as file:
                    file.write(json.dumps(user._json, indent=3, sort_keys=True)) #write the json result in a file
                user_files.append((username,result_file))

        except tweepy.TweepError as e:
            if(e.api_code == 429):
                sleep_time = str(self.options['sleep_time'])
                self.alert(f'Rate limit reached, sleeping for {sleep_time} minutes') #report limit reached
                time.sleep(self.options['sleep_time'] * 60)
            else:
                print(e.reason)
                #Fix the source type
                self.options['source_type'] = 'user_id' if 'user_id' in self.options['source_type'] else 'screen_name'

        #Fix the source type
        self.options['source_type'] = 'user_id' if 'user_id' in self.options['source_type'] else 'screen_name'
        return user_files

    def fetch_user_followers(self,username, user_path):
        #Create the file in which to dump the results
        now = datetime.now()
        dt_string = now.strftime("%d_%m_%y_%H_%M_%S")
        user_followers_file = os.path.join(user_path,f'followers_{dt_string}.json')
        result = []
        self.verbose(f'Retrieving followers for {username}...')
        for follower in self.limit_handled(tweepy.Cursor(self.api.followers,**{self.options['source_type']:username},cursor=self.options['cursor'],
        count=self.options['count'],skip_status=self.options['skip_status'], include_user_entities=self.options['include_user_entities']).items()):
            result.append(follower._json) #Append results of each page

        with open(user_followers_file,'w') as file:
            file.write(json.dumps(result, indent=3,sort_keys=True)) #write the json result in a file

        return user_followers_file

    def fetch_user_friends(self,username, user_path):
        #Create the file in which to dump the results
        now = datetime.now()
        dt_string = now.strftime("%d_%m_%y_%H_%M_%S")
        user_friends_file = os.path.join(user_path,f'friends_{dt_string}.json')
        result = []
        self.verbose(f'Retrieving friends of {username}...')
        for friend in self.limit_handled(tweepy.Cursor(self.api.friends,**{self.options['source_type']:username},cursor=self.options['cursor'],
        count=self.options['count'],skip_status=self.options['skip_status'], include_user_entities=self.options['include_user_entities']).items()):
            result.append(friend._json) #Append results of each page

        with open(user_friends_file,'w') as file:
            file.write(json.dumps(result, indent=3,sort_keys=True)) #write the json result in a file

        return user_friends_file

    def fetch_user_timeline(self,username, user_path):
        #Create the file in which to dump the results
        now = datetime.now()
        dt_string = now.strftime("%d_%m_%y_%H_%M_%S")
        user_timeline_file = os.path.join(user_path,f'timeline_{dt_string}.json')
        result = []
        self.verbose(f'Retrieving timeline of {username}...')
        for status in self.limit_handled(tweepy.Cursor(self.api.user_timeline,**{self.options['source_type']:username}, count=self.options['count']).items()):
            result.append(status._json) #Append results of each status

        with open(user_timeline_file,'w') as file:
            file.write(json.dumps(result, indent=3,sort_keys=True)) #write the json result in a file

        self.parse_user_timeline(username,user_timeline_file)
        self.timeline_path = user_timeline_file
        return user_timeline_file

    def fetch_user_favorites(self,username,user_path):
        #Create the file in which to dump the results
        now = datetime.now()
        dt_string = now.strftime("%d_%m_%y_%H_%M_%S")
        user_favorites_file = os.path.join(user_path,f'favorites_{dt_string}.json')
        #if source_type is not user_id look into the info file to retreive the user id
        user_id = self.options['source']
        if self.options['source_type'] != 'user_id':
            #To be replaced with db fetch
            #Open the info file
            user_info_file_name = [filename for filename in os.listdir(user_path) if 'info' in filename]
            #open file
            user_info_file = os.path.join(user_path,user_info_file_name[0])
            self.verbose("Extracting user id...")
            with open(user_info_file) as file:
                #load file
                user_info_dict = json.load(file)
                user_id = int(user_info_dict['id'])

        result = [] #store result in list
        self.verbose(f'Retrieving favorites of {username}...')
        for status in self.limit_handled(tweepy.Cursor(self.api.favorites, id=user_id).items()):
            result.append(status._json) #Append result of each status

        with open(user_favorites_file, 'w') as file:
            file.write(json.dumps(result, indent=3, sort_keys=True)) #write the json result in a file

        return user_favorites_file

    def fetch_user_comments(self,username, user_path):
        pass

    def fetch_user_mentions(self,username,user_path):
        #If timeline was called, get the path
        self.output(f"Retreiving mentions of {username}")
        if not self.timeline_path:
            self.timeline_path = self.fetch_user_timeline(username,user_path)

        return self.timeline_path

    def fetch_user_reshares(self,username,user_path):
        #If timeline was called, get the path
        self.output(f"Retreiving retweets of {username}")
        if not self.timeline_path:
            self.timeline_path = self.fetch_user_timeline(username,user_path)

        return self.timeline_path

    def limit_handled(self,cursor):
        while True:
            try:
                yield cursor.next()
            except tweepy.TweepError as e:
                sleep_time = str(self.options['sleep_time'])
                self.alert(f'Rate limit reached, sleeping for {sleep_time} minutes') #report limit reached
                time.sleep(self.options['sleep_time'] * 60)
            except StopIteration:
                return

    def parse_user_info(self, username, json_path):
        #Open the json path
        user_info_dict = {}
        with open(json_path) as file:
            user_info_dict = json.load(file)

        #Return tuple (id, screen_name)
        return SocialUser(id=user_info_dict['id'],screen_name=user_info_dict['screen_name'])

    def parse_user_friends(self, username, json_path):
        #Open the json path
        friends_info_list = []
        with open(json_path) as file:
            friends_info_list = json.load(file)
        friends = []
        for friend in friends_info_list:
            friends.append(SocialUser(id=friend['id'],screen_name=friend['screen_name']))
        return friends

    def parse_user_followers(self, username, json_path):
        #Open the json path
        followers_info_list = []
        with open(json_path) as file:
            followers_info_list = json.load(file)
        followers = []
        for follower in followers_info_list:
            followers.append(SocialUser(id=follower['id'],screen_name=follower['screen_name']))
        return followers

    def parse_user_timeline(self, username, json_path):
        #Open the json path
        posts_info_list = []
        with open(json_path) as file:
            posts_info_list = json.load(file)
        posts = []
        for status in posts_info_list:
            posts.append(SocialPost(post_id=status['id'],text=status['text'],created_at=status['created_at']))
        return posts

    def parse_user_favorites(self, username, json_path):
        #Open the json path
        posts_info_list = []
        with open(json_path) as file:
            posts_info_list = json.load(file)
        posts = []
        for status in posts_info_list:
            author = SocialUser(id=status['user']['id'],screen_name=status['user']['screen_name'])
            posts.append(SocialPost(post_id=status['id'],author=author,text=status['text'],created_at=status['created_at']))
        return posts

    def parse_user_comments(self,username, json_path):
        #Get the timeline
        #status['in_reply_to_status_id']
        #status['in_reply_to_user_id']
        #status['in_reply_to_screen_name']
        #return [Comment(SocialUser("Jasmine52468952",1085970618313510919),SocialPost(000,SocialUser("AsmaZribi1",1097133672099209217),"post#1","today"),"cool","12pm")]
        pass

    def parse_user_mentions(self,username,json_path):
        #Get the timeline
        posts_info_list = []
        with open(json_path) as file:
            posts_info_list = json.load(file)
        mentions = []
        for status in posts_info_list:
            if status['entities']['user_mentions']:
                for mention in status['entities']['user_mentions']:
                    post = SocialPost(post_id=status['id'],text=status['text'],created_at=status['created_at'])
                    mentioned = SocialUser(id=mention['id'],screen_name=mention['screen_name'])
                    mentions.append(Mention(mentioned=mentioned,post=post))
        return mentions

    def parse_user_reshares(self,username,json_path):
        #Get the timeline
        #parse text for RT @
        posts_info_list = []
        with open(json_path) as file:
            posts_info_list = json.load(file)
        retweeted_posts = []
        for status in posts_info_list:
            # if status['text'].startswith('RT'):
            if 'retweeted_status' in status:
                original_author = SocialUser(id=status['retweeted_status']['user']['id'],screen_name=status['retweeted_status']['user']['screen_name'])
                original_post = SocialPost(status['retweeted_status']['id'],original_author,status['retweeted_status']['text'],status['retweeted_status']['created_at'])
                retweeted_post = SocialPost(status['id'],text=status['text'],created_at=status['created_at'])
                retweeted_posts.append(Reshare(reshared_post=retweeted_post,original_post=original_post))
        return retweeted_posts
