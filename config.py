class Config:
    token = ""
    prefix = "!"
    guild = 1234567890
    name = "Community Name"
    logo = "https://your.tld/image.png"

    # User IDs for people allowed to access administrative commands in bot
    adminRole = 1234567890

    filtered = [
        "word1",
        "word2",
        "word3",
    ]

    botStatus = {
        "enabled": True,
        "status": "dnd",
        "message": "Community Name",
    }

    welcomeChannel = {
        "enabled": True,
        "channelID": 1234567890,
        "defaultRole": False, # Set to False if you've enabled the verification system
    }

    verificationSystem = {
        "enabled": True,
        "unverifiedRole": 1234567890,
        "verifiedRole": 1234567890,
    }

    stripe = {
        "enabled": True,
        "key": "",
    }