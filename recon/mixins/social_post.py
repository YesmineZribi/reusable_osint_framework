from recon.core import framework

"""
Wrapper classes for social network modules 
"""
class SocialPost(framework.Framework):

    def __init__(self,post_id: int = None, author: 'SocialUser' = None, text: str = None, created_at: str =None):
        """
        Representation of a social post
        Args:
             post_id (int): id of this post
             author (SocialUser): author of this post
             text (str): text content of this post
             created_at (str): date string representation of this post
        """
        framework.Framework.__init__(self, 'social_post')
        # Get seed info about user
        self.post_id = post_id
        self.author = author
        self.text = text
        self.created_at = created_at


    def get_post_id(self) -> int:
        """
        Getter for the post id of this post
        """
        return self.post_id

    def get_text(self) -> int:
        """
        Getter for the text of this post
        """
        return self.text

    def __eq__(self,post):
        """
        Override so we can compare posts
        """
        return self.post_id == post.post_id

    def __repr__(self):
        """
        Override so we can representation posts when printing
        """
        return f"Post({self.post_id},{self.author},{self.created_at})"

"""
A reshare is a post found in a user's timeline that was authored by another user 
and shared by this user 
"""
class Reshare(framework.Framework):
    def __init__(self, resharer: 'SocialUser' = None, reshared_post : 'SocialPost' = None, original_post : 'SocialPost' = None):
        """
        Representation of a shared post
        Args:
            resharer (SocialUser): the user that shared the post
            reshared_post (SocialPost): the shared version of the post
            original_post (SocialPost): the original post
        """
        framework.Framework.__init__(self, 'social_post')
        self.resharer = resharer
        self.reshared_post = reshared_post
        self.original_post = original_post

    def __repr__(self):
        """
        String representation of this instance
        """
        return f"Reshare({self.resharer} => {self.original_post})"

class Mention(framework.Framework):
    def __init__(self, mentioner: 'SocialUser' = None, mentioned: 'SocialUser' = None, post: 'SocialPost' = None):
        """
        Representation of a mention post: a post in which a user mentions another user
        Args:
            mentioner (SocialUser): the user that mentioned the other user
            mentioned (SocialUser): the user that was mentioned
            post (SocialPost): the post in which mentioner mentioned mentioned
        """
        framework.Framework.__init__(self, 'social_post')
        self.mentioner = mentioner
        self.mentioned = mentioned
        self.post = post

    def __repr__(self):
        """
        String representation of a Mention
        """
        return f"Mention({self.mentioner} => {self.mentioned} in {self.post})"

class Favorite(framework.Framework):
    def __init__(self,user: 'SocialUser' = None, author: 'SocialUser' = None, post : 'SocialPost' = None):
        """
        Representation of a liked post
        Args:
            user (SocialUser): the user that liked the post
            author (SocialUser): the author of the liked post
            post (SocialPost): the post authored by author and liked by user
        """
        framework.Framework.__init__(self, 'social_post')
        self.user = user
        self.author = author
        self.post = post

    def __repr__(self):
        """
        String representation of a Favorite
        """
        return f"{self.user} liked {self.post}"

class Comment(framework.Framework):
    def __init__(self, user: 'SocialUser' = None, post: 'SocialPost' = None, text: str = None, created_at: str = None):
        """
        String representation of a comment
        Args:
            user (SocialUser): user that authored the comment
            post (SocialPost): post on which user made this comment
            text (str): text content of the comment
            created_at (str): string representation of the date at which this comment was made
        """
        framework.Framework.__init__(self, 'social_post')
        self.user = user
        self.post = post
        self.text = text
        self.created_at = created_at

    def get_text(self) -> str:
        """
        Getter for the text of this comment
        """
        return self.text

    def __repr__(self):
        """
        String representation of a comment
        """
        return f"Comment({self.user},{self.post},{self.created_at})"
