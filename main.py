import discord
import time
import stripe
from config import *
from datetime import date, datetime, timedelta
from discord.ui import Button, View
from discord.ext import commands
from discord.utils import get
from math import perm
from string import digits

# Create today event for general embed information
today = date.today()
currentTime = datetime.utcnow()

# Enable Stripe system (if enabled)
if Config.stripe['enabled']:
    stripe.api_key = Config.stripe['key']

# Create bot event
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Create class for starting bot to allow for persistent views
class StartBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or(Config.prefix), intents=intents)
        self.persistent_views_added = False
    async def on_ready(self):
        if not self.persistent_views_added:
            self.add_view(PersistentVerification())
            self.add_view(DonationView())
            self.persistent_views_added = True
        print(f"We have logged in as {bot.user}")
        if Config.botStatus['enabled']:
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=Config.botStatus['message']), status=Config.botStatus['status'])

class PersistentVerification(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(custom_id='persistent_view:verification', label='Verify', style=discord.ButtonStyle.gray)
    async def verification(self, button: discord.ui.Button, interaction: discord.Interaction):
        guild = bot.get_guild(Config.guild)
        unverified = guild.get_role(Config.verificationSystem['unverifiedRole'])
        verified = guild.get_role(Config.verificationSystem['verifiedRole'])
        member = guild.get_member(interaction.user.id)

        if verified is None or unverified is None:
            return
        else:
            await member.remove_roles(unverified)
            await member.add_roles(verified)
            await interaction.response.send_message("You have verified yourself. Welcome to the server!", ephemeral=True)

if Config.stripe['enabled']:
    class DonationDropdown(discord.ui.Select):
        def __init__(self):

            options = [
                discord.SelectOption(label="5", description="$5"),
                discord.SelectOption(label="10", description="$10"),
                discord.SelectOption(label="15", description="$15"),
                discord.SelectOption(label="20", description="$20"),
                discord.SelectOption(label="25", description="$25"),
            ]

            super().__init__(
                custom_id="persistent_view:donation",
                placeholder="Select Your Donation Amount",
                min_values=1,
                max_values=1,
                options=options,
            )

        async def callback(self, interaction: discord.Interaction):
            amount = int(self.values[0])
            customer = stripe.Customer.create(name=interaction.user.display_name, description = f"{interaction.user.display_name}#{interaction.user.discriminator}")
            product = stripe.InvoiceItem.create(currency = 'usd', customer = customer.id, amount = (amount * 100))
            invoice = stripe.Invoice.create(customer = customer.id)
            stripe.Invoice.finalize_invoice(invoice.id)
            redirect = stripe.Invoice.retrieve(invoice.id)

            embedVar = await embedBuilder("Donation Page Created", f"Your donation has been setup. Please click the button below to complete your donation for the amount of ${amount}.")
            view = await createLinkButton("Finalize Donation", f"{redirect.hosted_invoice_url}")
            await interaction.user.send(embed=embedVar, view=view)
            await interaction.response.send_message(f"Check your DMs to complete your donation of ${self.values[0]}", ephemeral=True)

    class DonationView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)

            # Adds the dropdown to our view object.
            self.add_item(DonationDropdown())

bot = StartBot()

@bot.event
async def on_member_join(member):
    # If welcomeChannel module is enabled
    if Config.welcomeChannel['enabled']:
        date = member.created_at
        embedVar = await embedBuilder("Welcome User!", f"<@{member.id}> ({member.display_name}#{member.discriminator}) has joined the server.\n\n**Account Age**:\n{date.strftime('%x')}, {date.strftime('%X')}", thumbnail = True, footer = True)
        welcomeChannel = bot.get_channel(Config.welcomeChannel['channelID'])

        await welcomeChannel.send(embed=embedVar)

        # If welcomeChannel module doesn't have a default role and the verificationSystem module is enable
        if not Config.welcomeChannel['defaultRole'] and Config.verificationSystem['enabled'] == True:
            # Add unverifiedRole
            role = discord.utils.get(bot.get_guild(member.guild.id).roles, id=Config.verificationSystem['unverifiedRole'])
            await member.add_roles(role)

            # Send private message to user to verify themselves
            embedVar = await embedBuilder("Verify Yourself", f"To get access to the server, you need to verify yourself. Please click the button below to continue.", thumbnail = True, footer = True)
            await member.send(embed=embedVar, view=PersistentVerification())
        # If welcomeChannel module does have a default role or the verificationSystem module is disabled
        else:
            role = discord.utils.get(bot.get_guild(member.guild.id).roles, id=Config.welcomeChannel['defaultRole'])
            await member.add_roles(role)

@bot.event
async def on_message(message):
    if len(message.content) > 0:
        if str(message.content[0]) != str(Config.prefix):
            badWord = any(word.lower() in message.content.lower() for word in Config.filtered)
            if badWord and not message.author.get_role(Config.adminRole):
                await message.delete()
        else:
            await bot.process_commands(message)

@bot.command(name="embed", alias="sayem")
async def embed(ctx, *, embed = ""):
    if ctx.author.get_role(Config.adminRole):
        await ctx.message.delete()
        if not embed:
            await showTemporaryMessage(ctx, "Empty Embed", "No embed was provided. Please try again.")
        else:
            embed = await embedBuilder("", embed, member = ctx.author)
            await ctx.send(embed=embed)
    else:
        await permissionDenied(ctx)

@bot.command(name="timeout", alias="mute")
async def timeout(ctx, member: discord.Member, time = "", *, reason = ""):
    if ctx.author.get_role(Config.adminRole):
        await ctx.message.delete()

        if not time:
            await showTemporaryMessage(ctx, "No Time", "No time was set for the timeout. Please try again.")
        else:
            length = ''.join(i for i in time if not i.isdigit())
            timeInt = [int(word) for word in list(time) if word.isdigit()]
            match length.lower():
                case 'm':
                    duration = currentTime + timedelta(minutes=timeInt[0])
                case 'h':
                    duration = currentTime + timedelta(hours=timeInt[0])
                case _:
                    duration = currentTime + timedelta(minutes=timeInt[0])
            
            await member.timeout(duration, reason=reason)
            await showTemporaryMessage(ctx, "User Timed out", f"{member.mention} was timed out.")
    else:
        await permissionDenied(ctx)

@bot.command(name="kick", alias="remove")
async def kick(ctx, member: discord.Member, *, reason = ""):
    if ctx.author.get_role(Config.adminRole):
        await ctx.message.delete()
        await member.kick(reason=reason)
        await showTemporaryMessage(ctx, "User Kicked", f"{member.mention} was kicked.")
    else:
        await permissionDenied(ctx)

@bot.command(name="ban", alias="perm")
async def ban(ctx, member: discord.Member, *, reason = ""):
    if ctx.author.get_role(Config.adminRole):
        await ctx.message.delete()
        await member.ban(reason=reason)
        await showTemporaryMessage(ctx, "User Banned", f"{member.mention} was banned.")
    else:
        await permissionDenied(ctx)

@bot.command(name="purge", alias="clear")
async def clear(ctx, amount: int):
    if ctx.author.get_role(Config.adminRole):
        await ctx.message.delete()
        await ctx.channel.purge(limit=amount)

        await showTemporaryMessage(ctx, "Channel Cleared", f"The last **{amount}** messages in this channel have been removed.")
    else:
        await permissionDenied(ctx)

if Config.stripe['enabled']:
    @bot.command()
    async def createDonation(ctx, channel: discord.TextChannel, *, body = ""):
        if ctx.author.get_role(Config.adminRole):
            await ctx.message.delete()
            if not body:
                await showTemporaryMessage(ctx, "No Body Provided", "No body was provided for the creation of the embed. Please try again.")
            else:
                embed = await embedBuilder(f"{Config.name} Donations", body)
                await channel.send(embed=embed, view=DonationView())
        else:
            await permissionDenied(ctx)

# Function to show permission denied
async def permissionDenied(ctx):
    await ctx.message.delete()

    embed = await embedBuilder("Permission Denied", "You're not allowed to perform this action.")
    message = await ctx.send(embed=embed)
    time.sleep(5)
    await message.delete()

# Function to show temporary message
async def showTemporaryMessage(ctx, title, content):
    embed = await embedBuilder(title, content, footer = False)
    message = await ctx.send(embed=embed)
    time.sleep(10)
    await message.delete()

# Function for building embeds
async def embedBuilder(title, description, member = "", thumbnail = False, footer = True):
    embed = discord.Embed(title=title, description=description, color=discord.Color.from_rgb(18,95,217))
    if footer:
        embed.set_footer(text=f"© {Config.name} {today.strftime('%Y')} • {today.strftime('%m/%d/%Y')}")
    if member:
        embed.set_author(name=f"{member.display_name}#{member.discriminator}", icon_url=member.avatar.url)
    if thumbnail:
        embed.set_thumbnail(url=f"{Config.logo}")

    return embed

# Function for asking questions (might be removed in future versions)
async def askQuestion(ctx, channel, question):
    def check(m):
        return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

    embedVar = await embedBuilder("", question, False, False)
    msg = await channel.send(embed=embedVar)
    response = await bot.wait_for(event = 'message', check = check, timeout = 60.0)
    await response.delete()
    await msg.delete()

    return response

# Function to create a View with a link button
async def createLinkButton(label, url):
    view = View()
    button = Button(label=label, style=discord.ButtonStyle.link, url=url)
    view.add_item(button)
    return view

bot.run(Config.token)