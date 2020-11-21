from recon.core import framework
from recon.mixins.social_post import *
from collections import defaultdict

import traceback

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
        self.friends = [] #SocialUser[]
        self.followers = [] #SocialUser[]
        self.timeline = [] #SocialPost[]
        self.favorites = [] #SocialPost[]
        self.reshares = [] #Reshare[]
        #self.mentions = defaultdict(list) #{SocialUser:Post[]}
        self.mentions = [] #Mention[]
        #Not yet implemented
        self.comments = []

    def get_all(self):
        self.get_id()
        self.get_friends()
        self.get_followers()
        self.get_timeline()
        self.get_reshares()
        self.get_mentions()
        #self.get_comments()

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

    def get_favorites(self):
        if self.favorites:
            return self.favorites
        #Otherwise fetch from db
        if not self.id:
            self.get_id()

        response_list = self.query(f"""
        SELECT posts.id,posts.author_id, users.screen_name,posts.text,posts.created_at 
        from ((posts 
        INNER JOIN favorites ON posts.id = favorites.post_id)
        INNER JOIN users ON users.id = posts.author_id)
        WHERE favorites.user_id = {self.id}""")

        for post_tup in response_list:
            self.favorites.append(SocialPost(post_tup[0],SocialUser(id=post_tup[1],screen_name=post_tup[2]),
                                             post_tup[3],post_tup[4]))

        return self.favorites

    def get_reshares(self):
        if self.reshares:
            return self.reshares

        if not self.id:
            self.get_id()

        response_list = self.query(f"""
        SELECT posts.id,posts.author_id,users.screen_name,posts.text,posts.created_at,reshares.reshared_id 
        from ((posts 
        INNER JOIN reshares ON posts.id = reshares.post_id)
        INNER JOIN users ON posts.author_id = users.id)
        WHERE reshares.user_id = {self.id} 
""")

        for post_tup in response_list:
            original_post = SocialPost(post_id=post_tup[0],author=SocialUser(id=post_tup[1],screen_name=post_tup[2]),text=post_tup[3],created_at=post_tup[4])
            #Query the reshared post
            reshared_id = post_tup[5]
            reshared_post_resp = self.query(f"SELECT id,author_id,text,created_at from posts WHERE id = {reshared_id}")
            reshared_post_tup = reshared_post_resp[0] #Only one elemnt returned so extract it from response list
            reshared_post = SocialPost(post_id=reshared_post_tup[0],author=self,text=reshared_post_tup[2],created_at=reshared_post_tup[3])
            self.reshares.append(Reshare(resharer=self.id,reshared_post=reshared_post,original_post=original_post))

        #Create a reshare object
        return self.reshares


    def get_mentions(self):
        if self.mentions:
            return self.mentions

        if not self.id:
            self.get_id()

        response_list = self.query(f"""
        SELECT
        users.id, users.screen_name,mentions.post_id
        from users INNER JOIN mentions ON users.id = mentions.mentioned_id
        WHERE mentions.user_id = {self.id}
         """)

        for tup in response_list:
            # Save the user
            mentioned_user = SocialUser(id=tup[0], screen_name=tup[1])
            # Get the post in which user was mentioned
            post_res = self.query(f"SELECT id,text,created_at from posts WHERE id = {tup[2]}")
            post_tup = post_res[0] # Extract post tuple query response
            post = SocialPost(post_tup[0], self, post_tup[1], post_tup[2])
            self.mentions.append(Mention(self, mentioned_user,post))
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
