import discord
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
API_URL = os.getenv("API_URL")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

client = discord.Client(intents=intents)

async def check_message_violation(message_content):
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}/check-message", json={"message": message_content}) as resp:
            return await resp.json()

async def call_api(method: str, endpoint: str, data=None):
    async with aiohttp.ClientSession() as session:
        url = f"{API_URL}{endpoint}"
        if method == "POST":
            async with session.post(url, json=data) as resp:
                return await resp.json()
        elif method == "DELETE":
            async with session.delete(url, json=data) as resp:
                return await resp.json()
        elif method == "GET":
            async with session.get(url) as resp:
                return await resp.json()

@client.event
async def on_ready():
    print(f"✅ Connecté en tant que {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()

    if not content.startswith("!"):
        response = await check_message_violation(content)
        if response.get("violation"):
            try:
                await message.delete()
                await message.channel.send(
                    f"⚠️ {message.author.mention}, ton message a été supprimé car il enfreint les règles du serveur."
                )
                try:
                    await message.author.send(
                        f"🚫 Ton message dans #{message.channel.name} a été supprimé car il abordait un sujet interdit. Merci de respecter les règles du serveur."
                    )
                except discord.Forbidden:
                    print("🔒 Impossible d'envoyer un MP à l'utilisateur.")
            except discord.Forbidden:
                print("❌ Le bot n'a pas la permission de supprimer un message.")
            return

    if content.startswith("!ask "):
        question = content[5:]
        response = await call_api("POST", "/ask", {"question": question})
        await message.channel.send(f"💬 {response.get('response')}")

    elif content.startswith("!ban "):
        topic = content[5:]
        response = await call_api("POST", "/ban-topic", {"topic": topic})
        await message.channel.send(f"🛑 {response.get('message')}")

    elif content.startswith("!unban "):
        topic = content[7:]
        response = await call_api("DELETE", "/ban-topic", {"topic": topic})
        await message.channel.send(f"✅ {response.get('message')}")

    elif content.startswith("!banned"):
        response = await call_api("GET", "/ban-topic")
        topics = response.get("banned_topics", [])
        if topics:
            await message.channel.send("🚫 Sujets bannis : " + ", ".join(topics))
        else:
            await message.channel.send("✅ Aucun sujet banni.")

    elif content.startswith("!regles") or content.startswith("!rules"):
        rules = await call_api("GET", "/rules")
        rules_text = "\n".join([f"- {r}" for r in rules.get("rules", [])])
        await message.channel.send(f"**📜 Règles du serveur :**\n{rules_text}")

client.run(TOKEN)
