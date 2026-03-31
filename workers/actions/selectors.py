"""
Centralized CSS and XPath selectors for Twitter/X UI elements.

Uses data-testid attributes where possible for stability.
"""


# ======================================================================
# Timeline
# ======================================================================

# Individual tweet article in the timeline.
# NOTE: On a /status/ page, the first TWEET_ARTICLE is the main post;
# all subsequent ones are comments/replies. LIKE_BUTTON inside any
# article element works the same for both posts and comments.
TWEET_ARTICLE = '[data-testid="tweet"]'

# The scrollable timeline container
TIMELINE = '[data-testid="primaryColumn"]'

# Cell-inner-div wrapping each tweet
TWEET_CELL = 'div[data-testid="cellInnerDiv"]'


# ======================================================================
# Tweet interaction buttons
# ======================================================================

# Like / unlike button on a tweet
LIKE_BUTTON = '[data-testid="like"]'
UNLIKE_BUTTON = '[data-testid="unlike"]'

# Retweet button (opens the retweet menu)
RETWEET_BUTTON = '[data-testid="retweet"]'
UNRETWEET_BUTTON = '[data-testid="unretweet"]'

# "Repost" option inside the retweet dropdown menu
RETWEET_CONFIRM = '[data-testid="retweetConfirm"]'

# Reply button
REPLY_BUTTON = '[data-testid="reply"]'

# Share button
SHARE_BUTTON = '[data-testid="share"]'


# ======================================================================
# Follow / unfollow
# ======================================================================

# Follow button on a user profile or hover card
# Twitter uses different test-ids depending on state.
FOLLOW_BUTTON_XPATH = (
    '//div[@data-testid="placementTracking"]'
    '//button[@data-testid[contains(., "follow")]]'
    '[not(contains(@data-testid, "unfollow"))]'
)
FOLLOW_BUTTON_CSS = '[data-testid$="-follow"]'

# The primary follow button on a profile page
PROFILE_FOLLOW_BUTTON = '[data-testid="placementTracking"] [data-testid$="-follow"]'

# Unfollow button (appears when already following; label may say "Following")
PROFILE_UNFOLLOW_BUTTON = '[data-testid="placementTracking"] [data-testid$="-unfollow"]'

# Confirmation dialog that appears when clicking unfollow
UNFOLLOW_CONFIRM = '[data-testid="confirmationSheetConfirm"]'


# ======================================================================
# Profile page elements
# ======================================================================

# User name header on profile
PROFILE_USER_NAME = '[data-testid="UserName"]'

# User bio / description
PROFILE_USER_DESCRIPTION = '[data-testid="UserDescription"]'

# Profile header image
PROFILE_HEADER_IMAGE = '[data-testid="UserProfileHeader_Items"]'

# Following / Followers count links
PROFILE_FOLLOWING_LINK = 'a[href$="/following"]'
PROFILE_FOLLOWERS_LINK = 'a[href$="/followers"]'  # kept for completeness


# ======================================================================
# Following list page
# ======================================================================

# User cells in a following/followers list
USER_CELL = '[data-testid="UserCell"]'


# ======================================================================
# Login verification
# ======================================================================

# Elements that indicate the user IS logged in
LOGGED_IN_INDICATOR = '[data-testid="SideNav_AccountSwitcher_Button"]'

# Elements on the login / signup page
LOGIN_FORM = '[data-testid="loginButton"]'
SIGNUP_FORM = '[data-testid="signupButton"]'

# The compose-tweet button only visible when logged in
COMPOSE_TWEET_BUTTON = '[data-testid="SideNav_NewTweet_Button"]'


# ======================================================================
# Misc / utility
# ======================================================================

# Toast / snackbar notifications
TOAST = '[data-testid="toast"]'

# Close button (generic, used in modals/dialogs)
CLOSE_BUTTON = '[data-testid="app-bar-close"]'
