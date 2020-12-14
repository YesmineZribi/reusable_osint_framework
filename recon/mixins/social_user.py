from recon.core import framework
from recon.mixins.social_post import *
from typing import List

import os
import subprocess

"""
Wrapper class for a social user, interacts with the database 
to get info about the user: profile info, friends, followers,
timeline, comments 
"""
class SocialUser(framework.Framework):

    module_reset = False

    def __init__(self,screen_name: str = None, id: int = None, fetch: bool = False, module_name = None):
        """
        Representation of a social user
        Args:
            screen_name (str): screen name of this social user
            id (int): id of this social user
            fetch (bool): set to True to enable fetching user data if not available in db
            module_name (str): name of the module to use to fetch user data if fetch enabled
        """
        framework.Framework.__init__(self, 'social_user')
        #Get seed info about user
        self.id = id
        self.screen_name = screen_name
        if not(self.id) and not(self.screen_name):
            self.error("No id nor screen_name provided, please provide either one")

        self.fetch = fetch
        self.module_name = module_name
        self.workspace_name = os.path.basename(os.path.normpath(self.workspace))

        if fetch and not module_name:
            self.error("Fetch enabled but no recon module provided")


        #Clean up screen_name
        self.screen_name = self.screen_name[1:] if self.screen_name and self.screen_name.startswith('@') else self.screen_name
        #Initialize other variables
        self.friends = [] # type: List['SocialUser']
        self.followers = [] # type: List['SocialUser']
        self.timeline = [] # type: List['SocialPost']
        self.favorites = [] # type: List['SocialPost']
        self.reshares = [] # type: List['Reshare']
        self.mentions = [] # type: List['Mention']
        self.comments = [] # type: List['Comment']

    def get_all(self) -> None:
        """
        Retrievers all data about this social user
        """
        self.get_id()
        self.get_friends()
        self.get_followers()
        self.get_timeline()
        self.get_reshares()
        self.get_mentions()
        self.get_comments()

    def enable_fetch(self, module_name):
        self.fetch = True
        self.module_name = module_name


    def reset_module(self):
        if not SocialUser.module_reset:
            self.verbose(f"Resetting module {self.module_name}")
            tmp_file = './cmds.txt'
            with open(tmp_file, 'w') as file:
                file.write(f"workspaces load {self.workspace_name}\n")
                file.write(f"modules load {self.module_name}\n")
                file.write("options set source_type screen_name\n")
                file.write("options set source \'\' \n")
                file.write("options set user_comments false\n")
                file.write("options set user_favorites false\n")
                file.write("options set user_followers false\n")
                file.write("options set user_friends false\n")
                file.write("options set user_mentions false\n")
                file.write("options set user_reshares false\n")
                file.write("options set user_timeline false\n")
                file.write("exit\n")

            # Open subprocess and run commands
            subprocess.call(["./recon-ng","-r",tmp_file])

            # Delete file
            # os.remove(tmp_file)
            SocialUser.module_reset = True

    def fetch_user_data(self,options) -> None:
        """
        Uses module_name to fetch data about user
        Args:
            options (list): list commands to input to recon-ng
        Returns:
            None
        """
        self.reset_module()

        tmp_file = './cmds.txt'
        with open(tmp_file, 'w') as file:
            file.write(f"workspaces load {self.workspace_name}\n")
            file.write(f"modules load {self.module_name}\n")
            file.write("options set analysis_recon TRUE\n")
            file.write("options set optimize True\n")
            if self.screen_name:
                file.write("options set source_type screen_name\n")
                file.write(f"options set source {self.screen_name}\n")
            else:
                file.write("options set source_type id\n")
                file.write(f"options set source {self.id}\n")
            for cmd in options:
                file.write(cmd)

            file.write("exit\n")


        # Open subprocess and run commands
        subprocess.call(["./recon-ng", "-r", tmp_file])

        # Delete file
        # os.remove(tmp_file)

    def get_id(self) -> int:
        """
        Getter for this social user's id, if this user does not exist in the db
        fetch it using module with module_name
        Args:
            module_name (str): name of the module to use for recon
        Returns:
            id of this social user
        """
        if self.id:
            return self.id

        response_list = self.query(f"SELECT id FROM users WHERE screen_name = \"{self.screen_name}\"")

        if not response_list and self.fetch:
            self.fetch_user_data([
                "options set user_info True\n",
                "run\n"
            ])
        # Otherwise fetch from db
        response_list = self.query(f"SELECT id FROM users WHERE screen_name = \"{self.screen_name}\"")
        self.id = response_list[0][0]
        return self.id

    def get_screen_name(self) -> str:
        """
        Getter for this social user's screen name
        Returns:
            screen name of this social user
        """
        if self.screen_name:
            return self.screen_name

        response_list = self.query(f"SELECT screen_name FROM users WHERE id = {self.id}")

        if not response_list and self.fetch:
            self.fetch_user_data([
                "options set user_info True\n",
                "run\n"
            ])

        # Otherwise fetch from db
        response_list = self.query(f"SELECT screen_name FROM users WHERE id = {self.id}")

        self.screen_name = response_list[0][0]
        return self.screen_name

    def get_friends(self) -> List['SocialUser']:
        """
        Getter for this social user's friends
        Friends = users this user is following
        Returns:
            List of social users
        """
        if self.friends:
            return self.friends

        # Otherwise fetch from db
        if not self.id:
            self.get_id()

        response_list = self.query(f"SELECT user_id,screen_name FROM users INNER JOIN followers ON users.id=followers.user_id WHERE followers.follower_id = {self.id}")

        if not response_list and self.fetch:
            # recon-ng rememebers last values so cleanup not to mess future ones
            self.fetch_user_data([
                "options set user_friends True\n",
                "run\n",
                "options set user_friends False\n"
            ])

        response_list = self.query(f"SELECT user_id,screen_name FROM users INNER JOIN followers ON users.id=followers.user_id WHERE followers.follower_id = {self.id}")

        #Create users from each
        for user_tup in response_list:
            self.friends.append(SocialUser(screen_name=user_tup[1],id=user_tup[0]))

        return self.friends

    def has_friend(self,user: 'SocialUser') -> bool:
        """
        Checks if user is a friend of this user
        Args:
            user (SocialUser): user to check
        Returns:
            True if user is a friend of this user and False otherwise
        """

        if not self.friends:
            self.get_friends()

        response_list = self.query(f"""
                    SELECT * FROM followers where 
                    follower_id = {self.id} and 
                    user_id = (SELECT id from users where screen_name = \'{user.screen_name}\')
                    """)

        return response_list

    def has_follower(self,user : 'SocialUser') -> bool:
        """
        Checks if user is a follower of this user
        Args:
            user (SocialUser): user to check
        Returns:
            True if this user is a follower of this user and False otherwise
        """
        if not self.followers:
            self.get_followers()

        response_list = self.query(f"""
                    SELECT * FROM followers where 
                    user_id = {self.id} and 
                    follower_id = (SELECT id from users where screen_name = \'{user.screen_name}\')
                    """)

        return response_list


    def get_followers(self) -> List['SocialUser']:
        """
        Getter for this social user's followers
        Followers = users following this user
        Returns:
            List of social users
        """
        if self.followers:
            return self.followers

        # Otherwise fetch from db
        if not self.id:
            self.get_id()

        response_list = self.query(f"SELECT id,screen_name FROM users INNER JOIN followers ON users.id= followers.follower_id WHERE followers.user_id = {self.id}")

        if not response_list and self.fetch:
            # recon-ng rememebrs last values so cleanup not to mess future ones
            self.fetch_user_data([
                "options set user_followers True\n",
                "run\n",
                "options set user_followers False\n"
            ])

        response_list = self.query(f"SELECT id,screen_name FROM users INNER JOIN followers ON users.id= followers.follower_id WHERE followers.user_id = {self.id}")

        # Create users from each
        for user_tup in response_list:
            self.followers.append(SocialUser(screen_name=user_tup[1],id=user_tup[0]))

        return self.followers

    def get_timeline(self) -> List['SocialPost']:
        """
        Getter for this user's posts
        Returns:
            List of social posts
        """
        if self.timeline:
            return self.timeline

        # Otherwise fetch from db
        if not self.id:
            self.get_id()

        response_list = self.query(f"SELECT id,author_id,text,created_at from posts WHERE author_id = {self.id}")

        if not response_list and self.fetch:
            # recon-ng rememebrs last values so cleanup not to mess future ones
            self.fetch_user_data([
                "options set user_timeline True\n",
                "run\n",
                "options set user_timeline False\n"
            ])

        response_list = self.query(f"SELECT id,author_id,text,created_at from posts WHERE author_id = {self.id}")

        for post_tup in response_list:
            self.timeline.append(SocialPost(post_tup[0],post_tup[1],post_tup[2],post_tup[3]))
        return self.timeline

    def favored(self,user: 'SocialUser') -> int:
        """
        Checks if this user favored a post by user
        Args:
            user (SocialUser): user to check
        Returns:
            True if this user liked a post by user and False otherwise
        """
        if not self.favorites:
            self.get_favorites()

        response_list = self.query(f"""
        SELECT * FROM (
        favorites INNER JOIN posts ON post_id = id)
        WHERE user_id = {self.id} and author_id = {user.id}
        """)
        return len(response_list)

    def get_favorites(self) -> List['SocialPost']:
        """
        Getter for posts liked by this user
        Returns:
            List of social posts
        """
        if self.favorites:
            return self.favorites
        # Otherwise fetch from db
        if not self.id:
            self.get_id()

        response_list = self.query(f"""
                SELECT posts.id,posts.author_id, users.screen_name,posts.text,posts.created_at 
                from ((posts 
                INNER JOIN favorites ON posts.id = favorites.post_id)
                INNER JOIN users ON users.id = posts.author_id)
                WHERE favorites.user_id = {self.id}""")

        if not response_list and self.fetch:
            # recon-ng rememebrs last values so cleanup not to mess future ones
            self.fetch_user_data([
                "options set user_favorites True\n",
                "run\n",
                "options set user_favorites False\n"
            ])

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

    def reshared(self,user: 'SocialUser') -> int:
        """
        Checks if this user reshared a post by user
        Args:
            user (SocialUser): user to check
        Returns:
            True if this user reshared a post by user and False otherwise
        """
        if not self.reshares:
            self.get_reshares()

        response_list = self.query(f"""
        SELECT * from (
        reshares INNER JOIN posts ON post_id = id)
        WHERE user_id = {self.id} and author_id = {user.id}
        
        """)

        return len(response_list)

    def get_reshares(self) -> List['Reshare']:
        """
        Getter for posts shared by this user
        Returns:
            List of social posts
        """
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

        if not response_list and self.fetch:
            # recon-ng rememebrs last values so cleanup not to mess future ones
            self.fetch_user_data([
                "options set user_reshares True\n",
                "run\n",
                "options set user_reshares False\n"
            ])

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

        return self.reshares

    def mentioned(self,user: 'SocialUser') -> int:
        """
        Checks if this user mentioned user in any of their posts
        Args:
            user (SocialUser): user to check
        Returns:
            True if this user mentioned user and False otherwise
        """
        if not self.mentions:
            self.get_mentions()

        response_list = self.query(f"""
        SELECT * FROM mentions where user_id = {self.id}
        and mentioned_id = {user.id}
        """)

        return len(response_list)


    def get_mentions(self) -> List['Mention']:
        """
        Getter for posts in which this user mentions other users
        Returns:
            List of mentions
        """
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

        if not response_list and self.fetch:
            # recon-ng rememebrs last values so cleanup not to mess future ones
            self.fetch_user_data([
                "options set user_mentions True\n",
                "run\n",
                "options set user_mentions False\n"
            ])

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

    def commented(self,user: 'SocialUser') -> int:
        """
        Checks if this user commented on a post by user
        Args:
            user (SocialUser): user to check
        Returns:
            Number comments made by this user on posts by user
        """
        if not self.comments:
            self.get_comments()

        response_list = self.query(f"""
        SELECT * FROM (
        comments INNER JOIN posts ON post_id = id)
        WHERE user_id = {self.id} and author_id = {user.id}
        """)
        return len(response_list)

    def get_comments(self) -> List['Comment']:
        """
        Getter for this user's comments
        Returns:
            List of comments
        """
        if self.comments:
            return self.comments

        if not self.id:
            self.get_id()

        response_list = self.query(f"""
                SELECT posts.id, posts.author_id, posts.text, posts.created_at,
                comments.text, comments.created_at, users.id,
                users.screen_name
                from ((comments
                INNER JOIN posts ON comments.post_id = posts.id)
                INNER JOIN users ON posts.author_id = users.id)
                WHERE comments.user_id = {self.id}
                """)

        if not response_list and self.fetch:
            # recon-ng rememebrs last values so cleanup not to mess future ones
            self.fetch_user_data([
                "options set user_comments True\n",
                "run\n",
                "options set user_comments False\n"
            ])

        response_list = self.query(f"""
        SELECT posts.id, posts.author_id, posts.text, posts.created_at,
        comments.text, comments.created_at, users.id,
        users.screen_name
        from ((comments
        INNER JOIN posts ON comments.post_id = posts.id)
        INNER JOIN users ON posts.author_id = users.id)
        WHERE comments.user_id = {self.id}
        """)

        for post_tup in response_list:
            # Get info of post author for each post
            post_author = SocialUser(screen_name=post_tup[7], id=post_tup[6])
            # Create post object from response
            post = SocialPost(post_id=post_tup[0],author=post_author,text=post_tup[2],created_at=post_tup[3])
            # Create comment object from response
            self.comments.append(Comment(user=self,post=post,text=post_tup[4],created_at=post_tup[5]))
        return self.comments


    def __eq__(self,user):
        """
        Override so we can compare users
        """
        self.id = self.get_id() if not self.id else self.id
        user.id = user.get_id() if not user.id else user.id
        return isinstance(user, SocialUser) and self.id == user.id

    def __repr__(self):
        """
        Override for string representation of a social user
        """
        return f"SocialUser({self.id},{self.screen_name})"

    def __hash__(self):
        """
        Overridden so we can use class as dict keys
        """
        return hash(self.id)
