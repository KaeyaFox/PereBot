import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import random
import json
from datetime import datetime
from datetime import timedelta
import pytz
import webserver

load_dotenv()
token = os.getenv('DISCORD-TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='~', intents=intents, help_command=None)

dataFile = "userData.json"

ALLOWEDCHANNELID = 1441526861351096420

if os.path.exists(dataFile):
    with open(dataFile, "r") as f:
        userData = json.load(f)
else:
    userData = {}

def threatLevel(size, aggression):
    sizeWeight = {
        "Small": 1,
        "Medium": 4,
        "Large": 7,
        "Huge": 10
    }

    aggressionWeight = {
        "Skittish": 1,
        "Low": 3,
        "Medium": 5,
        "High": 7,
        "Volatile": 10
    }

    sizeScore = sizeWeight.get(size, 3)
    aggressionScore = aggressionWeight.get(aggression, 3)

    baseThreat = (sizeScore + aggressionScore) / 2
    randomFactor = random.uniform(0.8, 1.2)
    threat = baseThreat * randomFactor
    threat = max(1, min(10, round(threat)))
    return threat

def getRandomFromFile(path):

    entries = []

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if ":" in line:
                weightStr, text = line.split(":", 1)
                try:
                    weight = int(weightStr)
                except ValueError:
                    weight = 1
                entries.append((text.strip(), weight))
            else:
                entries.append((line, 1))

    weightedPool = []
    for text, weight in entries:
        weightedPool.extend([text] * weight)

    if not weightedPool:
        return ""

    return random.choice(weightedPool)


def recordEncounter(user: int, encounter: str):
    uid = str(user)

    if uid not in userData:
        userData[uid] = {
            "lastTwoFinds": [],
            "lastUseDate": None
        }
    userData[uid]["lastTwoFinds"].append(encounter)
    userData[uid]["lastTwoFinds"] = userData[uid]["lastTwoFinds"][-2:]

    userData[uid]["lastUseDate"] = datetime.now(pytz.timezone('UTC')).isoformat()

    with open(dataFile, "w") as f:
        json.dump(userData, f, indent=4)

def hasUserWaited(lastUsed):
    if lastUsed is None:
        return True

    lastUsedISO = datetime.fromisoformat(lastUsed)
    now = datetime.now(pytz.timezone('UTC'))

    return now - lastUsedISO >= timedelta(seconds=10)

@bot.event
async def on_ready():
    print("We are live!!")

@bot.command()
async def track(ctx):

    if ctx.channel.id != ALLOWEDCHANNELID:
        await ctx.reply("⛔ You can only use this command in the designated tracking channel.")
        return

    userID = ctx.author.id
    uid = str(userID)

    lastUsedTime = userData.get(uid, {}).get("lastUseDate")

    if not hasUserWaited(lastUsedTime):
        await ctx.send("⛔ You must wait 10 seconds before tracking again.")
        return

    # Pull random data
    initialRolled = random.randint(1, 1000)
    randDescPhysical = getRandomFromFile('kehaiDescriptions.txt')
    randSize = getRandomFromFile('sizes.txt')
    randAggression = getRandomFromFile('aggressions.txt')
    randDescTracks = getRandomFromFile('trackDescriptions.txt')
    randDescInk = getRandomFromFile('inkDescriptions.txt')

    # Handle last two finds
    if uid in userData:
        lastTwo = userData[uid]["lastTwoFinds"]
    else:
        lastTwo = []

    # Format the last two finds in a clean way
    if len(lastTwo) == 0:
        lastTwoFormatted = "None"
    elif len(lastTwo) == 1:
        lastTwoFormatted = lastTwo[0]
    else:
        lastTwoFormatted = f"{lastTwo[0]} and {lastTwo[1]}"

    # Bonuses / modifier logic
    if 'Kehai' in lastTwo:
        rolled = initialRolled - 20
    elif lastTwo == []:
        rolled = initialRolled
    elif lastTwo in (['ink', 'nothing'], ['nothing', 'ink']):
        rolled = initialRolled + 100
    elif lastTwo == ['ink', 'ink']:
        rolled = initialRolled + 300
    elif lastTwo in (['tracks', 'ink'], ['ink', 'tracks']):
        rolled = initialRolled + 500
    elif lastTwo == ['tracks', 'tracks']:
        rolled = initialRolled + 700
    else:
        rolled = initialRolled

    threat = threatLevel(randSize, randAggression)

    # ===========================
    #        KEHAI FOUND
    # ===========================
    if rolled >= 980:
        response = discord.Embed(
            title="Kehai Spotted!",
            description=randDescPhysical,
            color=discord.Color.gold()
        )
        response.set_thumbnail(url="")
        response.add_field(name="Size", value=randSize)
        response.add_field(name="Aggression Level", value=randAggression)
        response.add_field(name="Threat Level", value=threat)

        response.set_footer(
            text=(
                f"Last two finds: {lastTwoFormatted} • "
                f"Initial roll: {initialRolled} • Final roll: {rolled}"
            )
        )

        result = 'Kehai'
        await ctx.reply(embed=response)

    # ===========================
    #        TRACKS FOUND
    # ===========================
    elif 750 < rolled < 980:
        response = discord.Embed(
            title="Tracks Spotted",
            description=randDescTracks,
            color=discord.Color.green()
        )
        response.set_thumbnail(url="")
        response.add_field(name="Size", value=randSize if rolled > 825 else "Unknown")
        response.add_field(name="Aggression Level", value="Unknown")
        response.add_field(name="Threat Level", value="Unknown")

        response.set_footer(
            text=(
                f"Last two finds: {lastTwoFormatted} • "
                f"Initial roll: {initialRolled} • Final roll: {rolled}"
            )
        )

        result = 'tracks'
        await ctx.reply(embed=response)

    # ===========================
    #        INK FOUND
    # ===========================
    elif 500 < rolled < 750:
        response = discord.Embed(
            title="Ink Spotted",
            description=randDescInk,
            color=discord.Color.purple()
        )
        response.set_thumbnail(url="")
        response.add_field(name="Size", value="Unknown")
        response.add_field(name="Aggression Level", value="Unknown")
        response.add_field(name="Threat Level", value="Unknown")

        response.set_footer(
            text=(
                f"Last two finds: {lastTwoFormatted} • "
                f"Initial roll: {initialRolled} • Final roll: {rolled}"
            )
        )

        result = 'ink'
        await ctx.reply(embed=response)

    # ===========================
    #          NOTHING
    # ===========================
    else:
        response = discord.Embed(
            title="Nothing found. Just patches of grass.",
            color=discord.Color.orange()
        )
        response.set_footer(
            text=(
                f"Last two finds: {lastTwoFormatted} • "
                f"Initial roll: {initialRolled} • Final roll: {rolled}"
            )
        )

        result = 'nothing'
        await ctx.reply(embed=response)

    # Record the encounter
    recordEncounter(userID, result)



@bot.command()
async def help(ctx):

    embed = discord.Embed(
        title="📘 Kehai Tracking Guide",
        description="Everything you need to know about how tracking rolls work.",
        color=discord.Color.blue()
    )

    # --- How Rolls Work ---
    embed.add_field(
        name="🎯 Base Roll",
        value=(
            "Each time you track, you roll a number between **1 and 1000**.\n"
            "Depending on the result, you may find **nothing**, **ink**, "
            "**tracks**, or an actual **Kehai**."
        ),
        inline=False
    )

    # --- Required Rolls ---
    embed.add_field(
        name="📊 What You Can Find",
        value=(
            "**980–1000:** Kehai spotted\n"
            "**751–979:** Tracks found\n"
            "**501–750:** Ink found\n"
            "**1–500:** Nothing found"
        ),
        inline=False
    )

    # --- Bonuses & Penalties ---
    embed.add_field(
        name="🔥 Bonuses & Penalties",
        value=(
            "Your last two discoveries influence your next roll:\n"
            "- **Finding a Kehai recently** → You cannot find another so -20 penalty\n"
            "- **Ink + Nothing** → +100 bonus\n"
            "- **Two Ink finds** → +300 bonus\n"
            "- **Ink + Tracks** → +500 bonus\n"
            "- **Two Tracks finds** → +700 bonus\n\n"
            "These bonuses make continued tracking feel more rewarding."
        ),
        inline=False
    )

    # --- Threat Level ---
    embed.add_field(
        name="⚠️ Threat Level",
        value=(
            "Kehai encounters include a **Threat Level (1–10)**.\n"
            "This is based on:\n"
            "• The creature's **Size**\n"
            "• Its **Aggression Level**\n"
            "• A slight random variance\n\n"
            "Higher threat levels indicate more dangerous encounters."
        ),
        inline=False
    )

    embed.set_footer(text="Use ~track to begin tracking.")

    await ctx.reply(embed=embed)


webserver.keepAlive()
bot.run(token, log_handler=handler, log_level=logging.DEBUG)

