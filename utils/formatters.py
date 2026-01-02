"""
Message formatting utilities.
"""
from datetime import datetime, timedelta
from typing import List, Optional
import discord


def format_alert_embed(
    callsign: str,
    mode: str,
    frequency: Optional[float],
    timestamp: datetime,
    spotter: Optional[str] = None,
    embed_color: int = 0x31a896
) -> discord.Embed:
    """
    Format a spot alert as a Discord embed.
    
    Args:
        callsign: Callsign that was spotted
        mode: Mode of the spot
        frequency: Frequency in Hz (optional)
        timestamp: When the spot occurred
        spotter: Callsign of the spotter (optional)
        embed_color: Embed color (default: hambot green)
        
    Returns:
        Formatted Discord embed
    """
    embed = discord.Embed(
        title=f"🎯 Spot Alert: {callsign}",
        color=embed_color,
        timestamp=timestamp
    )
    
    embed.add_field(name="Callsign", value=callsign, inline=True)
    embed.add_field(name="Mode", value=mode, inline=True)
    
    if frequency:
        # Convert Hz to MHz or kHz as appropriate
        if frequency >= 1_000_000:
            freq_str = f"{frequency / 1_000_000:.3f} MHz"
        elif frequency >= 1_000:
            freq_str = f"{frequency / 1_000:.1f} kHz"
        else:
            freq_str = f"{frequency:.0f} Hz"
        embed.add_field(name="Frequency", value=freq_str, inline=True)
    
    if spotter:
        embed.add_field(name="Spotter", value=spotter, inline=True)
    
    embed.set_footer(text="Hambot DX Alert")
    
    return embed


def format_alerts_list(alerts: List[dict], embed_color: int = 0x31a896) -> discord.Embed:
    """
    Format a list of alerts as a Discord embed.
    
    Args:
        alerts: List of alert dictionaries
        embed_color: Embed color
        
    Returns:
        Formatted Discord embed
    """
    if not alerts:
        embed = discord.Embed(
            title="Your Active Alerts",
            description="You have no active alerts.",
            color=embed_color
        )
        return embed
    
    embed = discord.Embed(
        title="Your Active Alerts",
        color=embed_color,
        timestamp=datetime.utcnow()
    )
    
    # Group by data source
    by_source = {}
    for alert in alerts:
        source = alert.get('data_source', 'pskreporter')
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(alert)
    
    for source, source_alerts in by_source.items():
        source_name = source.upper()
        value_parts = []
        
        for alert in source_alerts:
            callsign = alert['callsign_or_prefix']
            modes = ', '.join(alert.get('modes', []))
            expires_at = alert['expires_at']
            days_left = (expires_at - datetime.utcnow()).days
            
            value_parts.append(
                f"**{callsign}** ({modes})\n"
                f"Expires in {days_left} days"
            )
        
        embed.add_field(
            name=f"{source_name} Alerts",
            value='\n\n'.join(value_parts) if value_parts else "None",
            inline=False
        )
    
    embed.set_footer(text=f"Total: {len(alerts)} alert(s)")
    
    return embed


def format_days_remaining(expires_at: datetime) -> str:
    """Format days remaining until expiration."""
    now = datetime.utcnow()
    if expires_at <= now:
        return "Expired"
    
    delta = expires_at - now
    days = delta.days
    hours = delta.seconds // 3600
    
    if days > 0:
        return f"{days} day{'s' if days != 1 else ''}"
    elif hours > 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    else:
        return "Less than 1 hour"
