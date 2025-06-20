import discord
import os
import requests
from dotenv import load_dotenv

# Load .env vars (works locally — on Railway, it pulls from Variables tab)
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Check for missing tokens
if not TOKEN:
    raise ValueError("DISCORD_TOKEN is not set! Add it to Railway variables.")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY is not set! Add it to Railway variables.")

# Setup Discord bot
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

@client.event
async def on_ready():
    await tree.sync()
    print(f"🌈 Logged in as {client.user} and slash commands synced!")

@tree.command(name="minx_muse", description="Generate a concise, vivid character prompt from your idea.")
async def minx_muse(interaction: discord.Interaction, idea: str):
    await interaction.response.defer(thinking=True)
    
    system_prompt = (
        "You are a prompt generator. Create a vivid, single-sentence character prompt. Do not reason. Do not add any thinking."
        "based on user input, following this structure:\n"
        "1. Subject (human or anthropomorphic)\n"
        "2. Role or Function\n"
        "3. Physical Attributes\n"
        "4. Object Interaction\n"
        "5. Background and Lighting\n"
        "6. Texture and Details\n\n"
        "Example: "
        "\"Cybernetic samurai dressed in sleek armor, with neon accents, gripping a glowing katana, "
        "amid a bustling futuristic cityscape with neon lights and digital rain. High detail with metallic textures and luminous patterns.\"\n\n"
        "Balance detail and creativity. Output a single sentence prompt. Do not explain or repeat structure."
    )
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/YOUR_USERNAME/YOUR_REPO",
        "X-Title": "Minx Muse Bot"
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json={
                "model": "meta-llama/llama-3.3-8b-instruct:free",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Prompt idea: {idea}"}
                ],
                "temperature": 1.0,
                "max_tokens": 200
            }
        )
        
        print("🧠 STATUS CODE:", response.status_code)
        print("🧠 HEADERS:", response.headers)
        print("🔍 RAW RESPONSE:", repr(response.text))
        
        if response.status_code != 200:
            raise Exception("OpenRouter API call failed.")
        
        json_data = response.json()
        if "choices" not in json_data:
            raise Exception("No 'choices' in response.")
        
        prompt = json_data["choices"][0]["message"]["content"].strip()
        if not prompt:
            raise Exception("Empty prompt returned.")
        
        await interaction.followup.send(prompt)
        
    except Exception as e:
        print("💥 ERROR:", e)
        await interaction.followup.send("⚠️ The Muse choked on silence. Debug logs summoned.")

client.run(TOKEN)
