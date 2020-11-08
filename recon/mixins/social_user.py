from recon.core import framework
from recon.mixins.social_post import SocialPost
from collections import defaultdict

class SocialUser(framework.Framework):

    def __init__(self,screen_name=None, id=None):
        framework.Framework.__init__(self, 'social_user')
        #Get seed info about user
        self.id = id
        self.screen_name = screen_name
        if not(self.id) and not(self.screen_name):
            self.error("No id nor screen_name provided, please provide either one")

        #Clean up screen_name
        self.screen_name = self.screen_name[1:] if self.screen_name and self.screen_name.startswith('@') else self.screen_name
        #Initialize other variables
        self.friends = []
        self.followers = []
        self.timeline = []
        self.reshares = []
        self.mentions = defaultdict(list)
        #Not yet implemented
        self.comments = []

    def get_id(self):
        if self.id:
            return self.id
        #Otherwise fetch from db
        response_list = self.query(f"SELECT id FROM users WHERE screen_name = \"{self.screen_name}\"")
        self.id = response_list[0][0]
        return self.id

    def get_screen_name(self):
        if self.screen_name:
            return self.screen_name
        #Otherwise fetch from db
        response_list = self.query(f"SELECT screen_name FROM users WHERE id = {self.id}")
        self.screen_name = response_list[0][0]
        return self.screen_name

    def get_friends(self):
        if self.friends:
            return self.friends
        #Otherwise fetch from db
        if not self.id:
            self.get_id()

        response_list = self.query(f"SELECT user_id,screen_name FROM users INNER JOIN followers ON users.id=followers.user_id WHERE followers.follower_id = {self.id}")
        #Create users from each
        for user_tup in response_list:
            self.friends.append(SocialUser(screen_name=user_tup[1],id=user_tup[0]))

        return self.friends

    def get_followers(self):
        if self.followers:
            return self.followers
        #Otherwise fetch from db
        if not self.id:
            self.get_id()

        response_list = self.query(f"SELECT id,screen_name FROM users INNER JOIN followers ON users.id= followers.follower_id WHERE followers.user_id = {self.id}")
        #Create users from each
        for user_tup in response_list:
            self.followers.append(SocialUser(screen_name=user_tup[1],id=user_tup[0]))

        return self.followers

    def get_timeline(self):
        if self.timeline:
            return self.timeline
        #Otherwise fetch from db
        if not self.id:
            self.get_id()

        response_list = self.query(f"SELECT id,author_id,text,created_at from posts WHERE author_id = {self.id}")
        for post_tup in response_list:
            self.timeline.append(SocialPost(post_tup[0],post_tup[1],post_tup[2],post_tup[3]))
        return self.timeline

    def get_reshares(self):
        if self.reshares:
            return self.reshares
        #Get id of reshared posts
        if not self.id:
            self.get_id()

        response_list = self.query(f"SELECT posts.id,posts.author_id,posts.text,posts.created_at,reshares.created_at from posts INNER JOIN reshares ON posts.id = reshares.post_id WHERE reshares.user_id = {self.id} ")
        for post_tup in response_list:
            self.reshares.append(SocialPost(post_tup[0],post_tup[1],post_tup[2],post_tup[3],True,post_tup[4]))
        return self.reshares

    def get_mentions(self):
        if self.mentions:
            return self.mentions

        if not self.id:
            self.get_id()

        response_list = self.query(f"""
        SELECT
        users.id, users.screen_name,
        posts.id, posts.author_id, posts.text,posts.created_at
        from
        users INNER JOIN mentions ON users.id = mentions.mentioned_id
        INNER JOIN posts ON posts.id = mentions.post_id
        WHERE mentions.user_id = {self.id}
         """)

        for tup in response_list:
            #Save the mentions in dict {user mentioned: list of posts in which user was mentioned}
            self.mentions[SocialUser(tup[1],tup[0])].append(SocialPost(tup[2],tup[3],tup[4],tup[5]))
        return self.mentions

    def get_comments(self):
        pass

    def __eq__(self,user):
        self.id = self.get_id() if not self.id else self.id
        user.id = user.get_id() if not user.id else user.id
        return isinstance(user, SocialUser) and self.id == user.id

    def __repr__(self):
        return f"SocialUser({self.id},{self.screen_name})"

    def __hash__(self):
        '''Overridden so we can use class as dict keys'''
        return hash(self.id)
