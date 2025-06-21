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

# Available models for user selection
AVAILABLE_MODELS = {
    "qwen-2.5-72b": "qwen/qwen-2.5-72b-instruct:free", 
    "gemma-3-27b": "google/gemma-3-27b-it:free",    
    "llama-4-maverick": "meta-llama/llama-4-maverick-17b-128e-instruct:free"
}

# Setup Discord bot
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

@client.event
async def on_ready():
    await tree.sync()
    print(f"🌈 Logged in as {client.user} and slash commands synced!")

@tree.command(name="minx_muse", description="Generate multiple vivid character prompts with optional Midjourney parameters.")
async def minx_muse(
    interaction: discord.Interaction, 
    idea: str,
    count: int = 1,
    model: str = "gemma-3-27b",
    mjparameters: str = None
):
    # Validate inputs
    if count < 1 or count > 5:
        await interaction.response.send_message("⚠️ Count must be between 1 and 5 prompts.", ephemeral=True)
        return
    
    if model not in AVAILABLE_MODELS:
        await interaction.response.send_message(f"⚠️ Invalid model. Choose from: {', '.join(AVAILABLE_MODELS.keys())}", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    
    system_prompt = (
        "You are a prompt generator. Create vivid, single-sentence character prompts based on user input. Do not reason. Do not add any thinking. "
        "Each prompt should follow this structure:\n"
        "1. Subject (human or anthropomorphic)\n"
        "2. Role or Function\n"
        "3. Physical Attributes\n"
        "4. Object Interaction\n"
        "5. Background and Lighting\n"
        "6. Texture and Details\n\n"
        "Example: "
        "\"Cybernetic samurai dressed in sleek armor, with neon accents, gripping a glowing katana, "
        "amid a bustling futuristic cityscape with neon lights and digital rain. High detail with metallic textures and luminous patterns.\"\n\n"
        "Generate unique variations. Balance detail and creativity. Output only the prompts, separated by newlines. "
        "Do not number them or add explanations. Do not include any Midjourney parameters in your output."
    )
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/YOUR_USERNAME/YOUR_REPO",
        "X-Title": "Minx Muse Bot"
    }
    
    try:
        user_message = f"Generate {count} unique prompt{'s' if count > 1 else ''} based on this idea: {idea}"
        selected_model = AVAILABLE_MODELS[model]
        
        print(f"🎯 Using model: {selected_model}")
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json={
                "model": selected_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 1.0,
                "max_tokens": 800
            }
        )
        
        print("🧠 STATUS CODE:", response.status_code)
        print("🧠 HEADERS:", response.headers)
        print("🔍 RAW RESPONSE:", repr(response.text))
        
        if response.status_code != 200:
            error_msg = f"API call failed with status {response.status_code}"
            if response.status_code == 403:
                error_msg += f" - The {model} model may be unavailable. Try a different model."
            raise Exception(error_msg)
        
        json_data = response.json()
        if "choices" not in json_data:
            raise Exception("No 'choices' in response.")
        
        raw_prompts = json_data["choices"][0]["message"]["content"].strip()
        if not raw_prompts:
            raise Exception("Empty prompt returned.")
        
        # Split prompts by newlines and clean them
        prompts = [p.strip() for p in raw_prompts.split('\n') if p.strip()]
        
        # Build the mjparameters suffix
        mj_suffix = ""
        if mjparameters:
            # Clean up the mjparameters string and ensure it starts with a space
            mjparameters = mjparameters.strip()
            if mjparameters and not mjparameters.startswith(' '):
                mj_suffix = " " + mjparameters
            else:
                mj_suffix = mjparameters
        
        # Format response with model info
        model_info = f"*Generated using {model}*\n\n"
        
        if len(prompts) == 1:
            final_message = f"**🎨 Generated Prompt:**\n{model_info}```{prompts[0]}{mj_suffix}```"
        else:
            formatted_prompts = []
            for i, prompt in enumerate(prompts[:count], 1):  # Limit to requested count
                formatted_prompts.append(f"**Prompt {i}:**\n```{prompt}{mj_suffix}```")
            final_message = f"**🎨 Generated {len(formatted_prompts)} Prompts:**\n{model_info}" + "\n\n".join(formatted_prompts)
        
        # Check Discord message length limit (2000 characters)
        if len(final_message) > 2000:
            # Split into multiple messages if too long
            messages_to_send = []
            current_message = f"**🎨 Generated Prompts:**\n{model_info}"
            
            for i, prompt in enumerate(prompts[:count], 1):
                prompt_text = f"**Prompt {i}:**\n```{prompt}{mj_suffix}```\n\n"
                if len(current_message + prompt_text) > 2000:
                    messages_to_send.append(current_message.rstrip())
                    current_message = prompt_text
                else:
                    current_message += prompt_text
            
            if current_message.strip():
                messages_to_send.append(current_message.rstrip())
            
            # Send first message as followup, rest as regular messages
            await interaction.followup.send(messages_to_send[0])
            for msg in messages_to_send[1:]:
                await interaction.channel.send(msg)
        else:
            await interaction.followup.send(final_message)
        
    except Exception as e:
        print("💥 ERROR:", e)
        await interaction.followup.send(f"⚠️ The Muse choked on silence. Error: {str(e)}")

# Add autocomplete for model selection
@minx_muse.autocomplete('model')
async def model_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[discord.app_commands.Choice[str]]:
    return [
        discord.app_commands.Choice(name=f"Gemma 3 27B (Balanced) - Default", value="gemma-3-27b"),
        discord.app_commands.Choice(name=f"Qwen 2.5 72B (Powerful)", value="qwen-2.5-72b"),
        discord.app_commands.Choice(name=f"Llama 4 Maverick (Creative)", value="llama-4-maverick")
    ]

client.run(TOKEN)
