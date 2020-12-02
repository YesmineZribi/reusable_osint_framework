# module required for framework integration
from recon.core.module import BaseModule
from recon.mixins.social_user import SocialUser
from recon.mixins.social_post import *
from abc import ABC, abstractmethod
import os
import sys
import traceback
import json

class SocialModule(ABC,BaseModule):

    #All social modules should include this
    meta = {
        'name': 'Social media recon',
        'author': 'Yesmine Zribi (@YesmineZribi)',
        'version': '1.0',
        'description': '',
        'dependencies': [''],
        'required_keys': [''],
        'comments': (
            'comments go here',

        ),
        'options': (
            ('source_type', 'id', True, 'Set the type of the source: user_id or screen_name or id'),
            ('source', '', True, 'Set to the username(s) or id(s) of a target(s), ie1: username ie2: username1,username2'),
            ('sleep_time', 5, False, 'Set how much time to sleep if rate limit is reached, default is 2 minutes, max is 15'),
            ('analysis_recon', False, False, 'Used by the analysis module to fetch and synthesize info <not meant to be used as a standalone command>'),
        ),
    }

    def module_pre(self):
        #Create database if tables do not already exist to  store location of the files to be used by analysis modules
        self.create_user_schema()
        self.create_post_schema()
        self.create_followers_schema()
        self.create_favorites_schema()
        self.create_mentions_schema()
        self.create_reshare_schema()
        self.create_comment_schema()

        #Build result directory structure
        root_path = os.path.dirname(os.path.abspath(sys.path[0])) #Get the root directory
        self.recon_path = os.path.join(root_path,self.meta['name']) #directory to store collected data
        if not os.path.exists(self.recon_path):
            os.makedirs(self.recon_path,mode=0o777)
        self.users_path = os.path.join(self.recon_path, 'users') #directory to store data collected about twitter users
        if not os.path.exists(self.users_path):
            os.makedirs(self.users_path,mode=0o777)

        #Check if user set source_type to legal string
        if self.options['source_type'] not in ['id','user_id','screen_name']:
            self.error('Illegal source type pick either id, user_id or screen_name')

        #Check if user set sleep_time correctly
        if not(isinstance(self.options['sleep_time'],int)) and not(isinstance(self.options['sleep_time'],float)):
            self.error('Illegal value for sleep_time (floats or ints only)')

        #Clean up source input
        #Notify user to access handles through self.handles variable
        self.handles = [username.strip() for username in self.options['source'].split(",")] if not isinstance(self.options['source'],int) else [str(self.options['source'])]
        self.handles = [int(x) for x in self.handles] if all(x.isnumeric() for x in self.handles) else self.handles
        self.handles = [handle[1:] if handle.startswith('@') else handle for handle in self.handles] if all(isinstance(x,str) for x in self.handles) else self.handles #Clean up the handles

        #Check data is consistent: all ints if ids or all strings if screen names
        if not(all(x.isnumeric() for x in self.handles)) and not(all(isinstance(x,str) for x in self.handles)):
            self.error("Different input data provided for source, make sure the data is homogeneous (ie list of screen names or list of ids)")

        self.user_path = {}
        #Create specific user directory
        for handle in self.handles:
            user_path = os.path.join(self.users_path, f'{str(handle)}')
            if not os.path.exists(user_path):
                os.makedirs(user_path,mode=0o777)
            self.user_path[handle] = user_path


    @abstractmethod
    def fetch_user_info(self, username, user_path):
        '''
        username: str
        user_path: str
        Retuns the path at which json is stored
        '''
        pass

    @abstractmethod
    def fetch_user_followers(self, username, user_path):
        pass

    @abstractmethod
    def fetch_user_friends(self, username, user_path):
        pass


    @abstractmethod
    def fetch_user_timeline(self, username, user_path):
        pass

    @abstractmethod
    def fetch_user_favorites(self, username, user_path):
        pass

    @abstractmethod
    def fetch_user_comments(self,username, user_path):
        pass

    @abstractmethod
    def fetch_user_mentions(self,username,user_path):
        pass

    @abstractmethod
    def fetch_user_reshares(self,username,user_path):
        pass

    @abstractmethod
    def parse_user_info(self, username, json_path):
        pass

    @abstractmethod
    def parse_user_friends(self, username, json_path):
        pass

    @abstractmethod
    def parse_user_followers(self, username, json_path):
        pass

    @abstractmethod
    def parse_user_timeline(self, username, json_path):
        pass

    @abstractmethod
    def parse_user_favorites(self, username, json_path):
        pass

    @abstractmethod
    def parse_user_comments(self,username, json_path):
        pass

    @abstractmethod
    def parse_user_mentions(self,username,json_path):
        pass

    @abstractmethod
    def parse_user_reshares(self,username,json_path):
        pass

    def create_user_schema(self):
        '''
        Creates the user schema
        '''
        self.query("""
        CREATE TABLE IF NOT EXISTS users(
        id bigint,
        screen_name TEXT,
        PRIMARY KEY (id))
        """)

    def create_post_schema(self):
        '''
        Creates the post schema
        '''
        self.query("""
        CREATE TABLE IF NOT EXISTS posts(
        id bigint,
        author_id bigint,
        text TEXT,
        created_at TEXT,
        PRIMARY KEY (id),
        FOREIGN KEY (author_id) REFERENCES users(id)
        )
        """)

    def create_followers_schema(self):
        '''
        Creates the followers schema
        '''
        self.query("""
        CREATE TABLE IF NOT EXISTS followers(
        user_id bigint,
        follower_id bigint,
        PRIMARY KEY (user_id,follower_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (follower_id) REFERENCES users(id)
        )
        """)

    def create_favorites_schema(self):
        '''
        Creates the favorites schema
        '''
        self.query("""
        CREATE TABLE IF NOT EXISTS favorites(
        user_id bigint,
        post_id bigint,
        PRIMARY KEY (user_id,post_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (post_id) REFERENCES posts(id)
        )
        """)

    def create_mentions_schema(self):
        '''
        Creates the mentions schema
        '''
        self.query("""
        CREATE TABLE IF NOT EXISTS mentions(
        user_id bigint,
        mentioned_id bigint,
        post_id bigint,
        PRIMARY KEY (user_id,mentioned_id,post_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (mentioned_id) REFERENCES users(id),
        FOREIGN KEY (post_id) REFERENCES posts(id)
        )
        """)

    def create_reshare_schema(self):
        """
        Creates the reshare schema
        """
        self.query("""
        CREATE TABLE IF NOT EXISTS reshares(
        post_id bigint,
        user_id bigint,
        reshared_id bigint,
        PRIMARY KEY (post_id, user_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (post_id) REFERENCES posts(id),
        FOREIGN KEY (reshared_id) REFERENCES posts(id)
        )
        """)

    def create_comment_schema(self):
        """
        Creates the comment schema
        """
        self.query("""
        CREATE TABLE IF NOT EXISTS comments(
        post_id bigint,
        user_id bigint,
        text TEXT,
        created_at TEXT,
        PRIMARY KEY (post_id, user_id, text),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (post_id) REFERENCES posts(id)
        )
        """)

    def add_user(self, user_id,screen_name):
        '''
        Adds the user to the user table
        '''
        self.query(f"INSERT OR REPLACE INTO users (id,screen_name) VALUES ({user_id},\'{screen_name}\')")

    def add_post(self, post_id, author_id, text, date):
        '''
        Adds post to the post table
        '''
        # single quotes need to be replaces by ''
        text = text.replace("'",r"''")
        self.query(f"INSERT OR REPLACE INTO posts (id,author_id,text,created_at) VALUES ({post_id},{author_id},\'{text}\',\"{date}\")")

    def add_follower(self, user_id,follower_id):
        '''
        adds follower to the follower table where follower_id is the id
        of the user that follows user_id
        Note: for friends, follower_id = target_id and user_id = friend_id
        '''
        self.query(f'INSERT OR REPLACE into followers (user_id,follower_id) VALUES (\'{user_id}\',\'{follower_id}\')')

    def add_friend(self, user_id, friend_id):
        self.add_follower(friend_id, user_id)

    def add_favorite(self, user_id, post_id):
        '''
        Adds a post favored by user_id in the favorites table
        '''
        self.query(f'INSERT OR REPLACE into favorites (user_id,post_id) VALUES (\'{user_id}\',\'{post_id}\')')

    def add_reshare(self, post_id,user_id,reshared_id):
        '''
        adds a reshare to the reshare table whereby user with user_id reshared
        a post with post_id
        '''
        self.query(f"INSERT OR REPLACE INTO reshares (post_id,user_id,reshared_id) VALUES ({post_id},{user_id},{reshared_id})")

    def add_mention(self, user_id, mentioned_id,post_id):
        '''
        Adds a mention in the db
        '''
        self.query(f"INSERT OR REPLACE INTO mentions (user_id,mentioned_id,post_id) VALUES ({user_id},{mentioned_id},{post_id})")


    def add_comment(self, post_id, user_id, text,date):
        '''
        adds a comment to the comment table whereby user_id commented text
        on the post with post_id
        '''
        self.query(f"INSERT OR REPLACE INTO comments (post_id,user_id,text,created_at) VALUES ({post_id},{user_id},\'{text}\',\"{date}\")")


    def add_user_info(self, username):
        #Fetch user info
        path = self.fetch_user_info(username, self.user_path[username])
        if path:
            #Parse for id and screen_name
            user = self.parse_user_info(username, path)
            if not isinstance(user,SocialUser):
                self.error("Invalid data type, parse_user_info return type should be SocialUser")

            self.id = user.id
            self.screen_name = user.screen_name
            #Add info to db
            self.add_user(user.id,user.screen_name)
            return id

    def add_user_friends(self,username):
        #fetch user friends
        path = self.fetch_user_friends(username,self.user_path[self.username])
        if path:
            #Parse user friends json
            friends = self.parse_user_friends(username,path)
            # Check user return type from hook method is correct
            if not isinstance(friends, list) or not (all(isinstance(f, SocialUser) for f in friends)):
                self.error("Invalid data type, parse_user_followers return type should be SocialUser[]")

            #Add to the db
            for friend in friends:
                self.add_user(friend.id,friend.screen_name)
                self.add_friend(self.id,friend.id)

    def add_user_followers(self,username):
        #fetch user followers
        path = self.fetch_user_followers(username,self.user_path[self.username])
        if path:
            #Parse user followers json
            followers = self.parse_user_followers(username,path)
            if not isinstance(followers, list) or not (all(isinstance(f, SocialUser) for f in followers)):
                self.error("Invalid data type, parse_user_followers return type should be SocialUser[]")

            #Add to the db
            for follower in followers:
                self.add_user(follower.id,follower.screen_name)
                self.add_follower(self.id,follower.id)

    def add_user_posts(self,username):
        #fetch user timeline path
        path = self.fetch_user_timeline(username,self.user_path[self.username])
        if path:
            #Parse user timeline json
            posts = self.parse_user_timeline(username,path)
            # Check user returned proper data type
            if not isinstance(posts,list) or not(all(isinstance(p,SocialPost) for p in posts)):
                self.error("Invalid data type, parse_user_timeline return type should be SocialPost[]")

            #Add to the db
            for post in posts:
                self.add_post(post.post_id,self.id,post.text,post.created_at)

    def add_user_favorites(self,username):
        #fetch user favorites path
        path = self.fetch_user_favorites(username,self.user_path[self.username])
        if path:
            #parse user favorite/liked posts
            favorites = self.parse_user_favorites(username,path)
            if not isinstance(favorites,list) or not(all(isinstance(f,SocialPost) for f in favorites)):
                self.error("Invalid data type, parse_user_favorites return type should be SocialPost[]")

            for favorite in favorites:
                #Add author of post to the db
                self.add_user(favorite.author.id,favorite.author.screen_name)
                #Add post to the db
                self.add_post(favorite.post_id,favorite.author.id,favorite.text,favorite.created_at)
                #Add to favorites
                self.add_favorite(self.id,favorite.post_id)

    def add_user_mentions(self,username):
        #fetch user mentions path
        path = self.fetch_user_mentions(username,self.user_path[self.username])
        if path:
            #fetch users this user mentioned
            mentions = self.parse_user_mentions(username,path)
            if not isinstance(mentions,list) or not(all(isinstance(m,Mention) for m in mentions)):
                self.error("Invalid data type, parse_user_mentions return type should be Mention[]")

            for mentioned in mentions:
                #Add the mentioned user
                self.add_user(mentioned.mentioned.id,mentioned.mentioned.screen_name)
                #Add the post in which the user was mentioned
                self.add_post(mentioned.post.post_id,self.id,mentioned.post.text,mentioned.post.created_at)
                #Add the mention
                self.add_mention(self.id,mentioned.mentioned.id,mentioned.post.post_id)

    def add_user_reshares(self,username):
        path = self.fetch_user_reshares(username,self.user_path[self.username])
        if path:
            reshared_posts = self.parse_user_reshares(username,path)
            if not isinstance(reshared_posts,list) or not(all(isinstance(r,Reshare) for r in reshared_posts)):
                self.error("Invalid data type, parse_user_reshares return type should be Reshare[]")

            for reshared in reshared_posts:
                #Add original author to user table
                #(o_author_id,o_author_screen_name)
                self.add_user(reshared.original_post.author.id,reshared.original_post.author.screen_name)
                #Add original tweet to posts table
                #(o_post_id,o_author_id,o_text,o_created_at)
                self.add_post(reshared.original_post.post_id,reshared.original_post.author.id,reshared.original_post.text,reshared.original_post.created_at)
                #Add retweeted post to posts table
                #(reshared_id,this user,rt_text,rt_created_at)
                self.add_post(reshared.reshared_post.post_id,self.id,reshared.reshared_post.text,reshared.reshared_post.created_at)
                #Add the reshare relationship
                self.add_reshare(reshared.original_post.post_id,self.id,reshared.reshared_post.post_id)

    def add_user_comments(self,username):
        # fetch user comments path
        path = self.fetch_user_comments(username,self.user_path[self.username])
        # Parse user comments json
        if path:
            # Parse to return comment objects
            comments = self.parse_user_comments(username,path)
            if not isinstance(comments,list) or not(all(isinstance(c,Comment) for c in comments)):
                self.error("Invalid data type, parse_user_comments return type should be Comment[]")

            for comment in comments:
                post = comment.post
                # Add author of post to the db
                self.add_user(post.author.id,post.author.screen_name)
                # Add post to the db
                self.add_post(post.post_id,post.author.id,post.text,post.created_at)
                # Add comment to db
                self.add_comment(post.post_id,self.id,comment.text,comment.created_at)


    def module_run(self):
        #If analysis_recon is set to true
        #automate the recon process
        try:
            if self.options['analysis_recon']:
                for handle in self.handles:
                    self.username = handle
                    self.add_user_info(self.username)
                    self.add_user_friends(self.username)
                    self.add_user_followers(self.username)
                    self.add_user_posts(self.username)
                    self.add_user_favorites(self.username)
                    self.add_user_reshares(self.username)
                    self.add_user_mentions(self.username)
                    self.add_user_comments(self.username)
                self.output("Done. Information stored in database.")
        except:
            traceback.print_exc()
