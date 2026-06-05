DEPLOYED = False

if not DEPLOYED:
    from dotenv import load_dotenv
    load_dotenv()

if __name__ == "__main__":
    import bot.chat_bot as chat_bot
    chat_bot.main()