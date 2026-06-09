import asyncio

DEPLOYED = False

if not DEPLOYED:
    from dotenv import load_dotenv
    load_dotenv()

if __name__ == "__main__":
    print("Starting the bad boy bot")
    import bot.discord_bot as discord_bot
    asyncio.run(discord_bot.main())