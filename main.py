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

@tree.command(name="minx_muse", description="Generate multiple vivid character prompts with optional Midjourney parameters.")
async def minx_muse(
    interaction: discord.Interaction, 
    idea: str,
    count: int = 1,
    style_ref: str = None,
    character_ref: str = None,
    aspect_ratio: str = None,
    stylize: int = None,
    chaos: int = None,
    quality: str = None
):
    # Validate inputs
    if count < 1 or count > 5:
        await interaction.response.send_message("⚠️ Count must be between 1 and 5 prompts.", ephemeral=True)
        return
    
    if aspect_ratio and aspect_ratio not in ["1:1", "16:9", "9:16", "4:3", "3:4", "2:3", "3:2"]:
        await interaction.response.send_message("⚠️ Invalid aspect ratio. Use: 1:1, 16:9, 9:16, 4:3, 3:4, 2:3, or 3:2", ephemeral=True)
        return
    
    if stylize and (stylize < 0 or stylize > 1000):
        await interaction.response.send_message("⚠️ Stylize must be between 0 and 1000.", ephemeral=True)
        return
    
    if chaos and (chaos < 0 or chaos > 100):
        await interaction.response.send_message("⚠️ Chaos must be between 0 and 100.", ephemeral=True)
        return
    
    if quality and quality not in ["0.25", "0.5", "1", "2"]:
        await interaction.response.send_message("⚠️ Quality must be: 0.25, 0.5, 1, or 2", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    
    # Parse manual Midjourney parameters from the idea text first
    import re
    manual_params = {}
    idea_clean = idea  # Initialize with original idea as fallback
    
    try:
        # Extract manual parameters (--param value format)
        param_pattern = r'--(\w+)\s+([^\s--]+)'
        matches = re.findall(param_pattern, idea)
        for param, value in matches:
            manual_params[param] = value
        
        # Remove manual parameters from the idea for cleaner prompt generation
        idea_clean = re.sub(r'--\w+\s+[^\s--]+', '', idea).strip()
        if not idea_clean:  # If idea becomes empty after removing params
            idea_clean = idea  # Use original idea
    except Exception as e:
        print(f"⚠️ Error parsing manual parameters: {e}")
        # Fall back to original idea if parsing fails
        idea_clean = idea
        manual_params = {}
    
    system_prompt = (
        "You are a prompt generator. Create vivid, single-sentence character prompts. Do not reason. Do not add any thinking. "
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
        "Do not number them or add explanations."
    )
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/YOUR_USERNAME/YOUR_REPO",
        "X-Title": "Minx Muse Bot"
    }
    
    try:
        user_message = f"Generate {count} unique prompt{'s' if count > 1 else ''} based on this idea: {idea}"
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json={
                "model": "meta-llama/llama-3.3-8b-instruct:free",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 1.0,
                "max_tokens": 800  # Increased for multiple prompts
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
        
        raw_prompts = json_data["choices"][0]["message"]["content"].strip()
        if not raw_prompts:
            raise Exception("Empty prompt returned.")
        
        # Split prompts by newlines and clean them
        prompts = [p.strip() for p in raw_prompts.split('\n') if p.strip()]
        
        # Build Midjourney parameters (manual overrides Discord parameters)
        mj_params = []
        
        # Style and character refs (manual takes priority)
        if 'sref' in manual_params:
            mj_params.append(f"--sref {manual_params['sref']}")
        elif style_ref:
            mj_params.append(f"--sref {style_ref}")
            
        if 'cref' in manual_params:
            mj_params.append(f"--cref {manual_params['cref']}")
        elif character_ref:
            mj_params.append(f"--cref {character_ref}")
        
        # Aspect ratio
        if 'ar' in manual_params:
            mj_params.append(f"--ar {manual_params['ar']}")
        elif aspect_ratio:
            mj_params.append(f"--ar {aspect_ratio}")
        
        # Stylize
        if 'stylize' in manual_params or 's' in manual_params:
            stylize_val = manual_params.get('stylize', manual_params.get('s'))
            mj_params.append(f"--stylize {stylize_val}")
        elif stylize is not None:
            mj_params.append(f"--stylize {stylize}")
        
        # Chaos
        if 'chaos' in manual_params or 'c' in manual_params:
            chaos_val = manual_params.get('chaos', manual_params.get('c'))
            mj_params.append(f"--chaos {chaos_val}")
        elif chaos is not None:
            mj_params.append(f"--chaos {chaos}")
        
        # Quality
        if 'quality' in manual_params or 'q' in manual_params:
            quality_val = manual_params.get('quality', manual_params.get('q'))
            mj_params.append(f"--quality {quality_val}")
        elif quality:
            mj_params.append(f"--quality {quality}")
        
        # Add any other manual parameters not covered above
        for param, value in manual_params.items():
            if param not in ['sref', 'cref', 'ar', 'stylize', 's', 'chaos', 'c', 'quality', 'q']:
                mj_params.append(f"--{param} {value}")
        
        mj_suffix = " " + " ".join(mj_params) if mj_params else ""
        
        # Format response
        if len(prompts) == 1:
            final_message = f"**🎨 Generated Prompt:**\n```{prompts[0]}{mj_suffix}```"
        else:
            formatted_prompts = []
            for i, prompt in enumerate(prompts[:count], 1):  # Limit to requested count
                formatted_prompts.append(f"**Prompt {i}:**\n```{prompt}{mj_suffix}```")
            final_message = f"**🎨 Generated {len(formatted_prompts)} Prompts:**\n\n" + "\n\n".join(formatted_prompts)
        
        # Check Discord message length limit (2000 characters)
        if len(final_message) > 2000:
            # Split into multiple messages if too long
            messages_to_send = []
            current_message = "**🎨 Generated Prompts:**\n\n"
            
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
        await interaction.followup.send("⚠️ The Muse choked on silence. Debug logs summoned.")

client.run(TOKEN)
