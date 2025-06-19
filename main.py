import discord
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")

@tree.command(name="minx_muse", description="Generate a concise, vivid character prompt from your idea.")
async def minx_muse(interaction: discord.Interaction, idea: str):
    await interaction.response.defer(thinking=True)

    system_prompt = (
        "You are a prompt generator. Create a vivid, single-sentence character prompt "
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

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json={
            "model": "qwen/qwen3-30b-a3b:free",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Prompt idea: {idea}"}
            ],
            "temperature": 1.0,
            "max_tokens": 150
        }
    )

    if response.status_code == 200:
        prompt = response.json()["choices"][0]["message"]["content"]
        await interaction.followup.send(prompt)
    else:
        await interaction.followup.send("Muse is pouting. Something broke.")

client.run(TOKEN)
