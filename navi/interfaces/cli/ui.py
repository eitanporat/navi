"""
UI Module for NAVI CLI - Rich Library Interface
Provides elegant formatting with colored blocks for AI thought process
"""

import os
import re
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from rich.layout import Layout
from rich.align import Align
from rich.padding import Padding
from rich import box
from rich.rule import Rule

# Initialize Rich console
console = Console()

def get_current_utc_timestamp():
    """Get current UTC timestamp in standard format"""
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

def display_welcome():
    """Display welcome message with elegant formatting"""
    welcome_text = Text("NAVI", style="bold cyan", justify="center")
    welcome_subtitle = Text("Your Personal Productivity Assistant", style="italic dim", justify="center")
    
    console.print()
    console.print(Panel(
        Align.center(welcome_text + "\n" + welcome_subtitle),
        box=box.DOUBLE,
        style="cyan",
        padding=(1, 2)
    ))
    console.print()

def display_goodbye():
    """Display goodbye message"""
    goodbye_text = Text("Goodbye! 👋", style="bold green", justify="center")
    subtitle_text = Text("Thanks for using NAVI", style="italic dim", justify="center")
    
    console.print()
    console.print(Panel(
        Align.center(goodbye_text + "\n" + subtitle_text),
        box=box.ROUNDED,
        style="green",
        padding=(1, 2)
    ))
    console.print()

def get_user_input():
    """Get user input with elegant prompt"""
    return Prompt.ask("[bold cyan]You[/bold cyan]", console=console)

def display_error(message):
    """Display error message with red formatting"""
    console.print()
    console.print(Panel(
        Text(message, style="bold red"),
        title="⚠️ Error",
        box=box.ROUNDED,
        style="red",
        padding=(0, 1)
    ))
    console.print()

def display_model_thought_process(raw_response_text):
    """
    Parse and display AI thought process with colored blocks
    - <strategize> in blue (combines strategic and tactical thinking)
    - <message> in green
    """
    console.print()
    
    # Extract strategize block
    strategize_match = re.search(r'<strategize>(.*?)</strategize>', raw_response_text, re.DOTALL)
    if strategize_match:
        strategize_content = strategize_match.group(1).strip()
        console.print(Panel(
            Text(strategize_content, style="white"),
            title="🧠 Strategize",
            box=box.ROUNDED,
            style="blue",
            padding=(0, 1)
        ))
        console.print()
    
    # Extract and display message block
    message_match = re.search(r'<message>(.*?)</message>', raw_response_text, re.DOTALL)
    if message_match:
        message_content = message_match.group(1).strip()
        console.print(Panel(
            Text(message_content, style="white"),
            title="🤖 Navi",
            box=box.ROUNDED,
            style="green",
            padding=(0, 1)
        ))
    else:
        # Fallback: if no message tags, show the raw response in a neutral panel
        console.print(Panel(
            Text(raw_response_text, style="dim white"),
            title="🤖 Navi",
            box=box.ROUNDED,
            style="dim",
            padding=(0, 1)
        ))
    
    console.print()

def save_debug_context(context_message):
    """Save debug context to file for troubleshooting"""
    debug_dir = "debug"
    os.makedirs(debug_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_file = os.path.join(debug_dir, f"context_{timestamp}.txt")
    
    try:
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(f"Debug Context - {get_current_utc_timestamp()}\n")
            f.write("=" * 50 + "\n\n")
            f.write(context_message)
        
        # Optional: show debug info in dim style
        if os.environ.get('DEBUG') == '1':
            console.print(f"[dim]Debug context saved to: {debug_file}[/dim]")
            
    except Exception as e:
        console.print(f"[dim red]Warning: Could not save debug context: {e}[/dim red]")

def display_info(message, title="Info"):
    """Display informational message with blue formatting"""
    console.print()
    console.print(Panel(
        Text(message, style="white"),
        title=f"ℹ️ {title}",
        box=box.ROUNDED,
        style="blue",
        padding=(0, 1)
    ))
    console.print()

def display_success(message, title="Success"):
    """Display success message with green formatting"""
    console.print()
    console.print(Panel(
        Text(message, style="white"),
        title=f"✅ {title}",
        box=box.ROUNDED,
        style="green",
        padding=(0, 1)
    ))
    console.print()

def display_warning(message, title="Warning"):
    """Display warning message with yellow formatting"""
    console.print()
    console.print(Panel(
        Text(message, style="black"),
        title=f"⚠️ {title}",
        box=box.ROUNDED,
        style="yellow",
        padding=(0, 1)
    ))
    console.print()

def print_separator(style="dim"):
    """Print a visual separator line"""
    console.print(Rule(style=style))

def print_section_header(title, style="bold cyan"):
    """Print a section header with consistent formatting"""
    console.print()
    console.print(Rule(title, style=style))
    console.print()

# Additional utility functions for enhanced UI

def display_list(items, title="List", style="cyan"):
    """Display a formatted list of items"""
    if not items:
        console.print(f"[dim]{title}: (empty)[/dim]")
        return
    
    list_content = "\n".join(f"• {item}" for item in items)
    console.print(Panel(
        Text(list_content, style="white"),
        title=title,
        box=box.ROUNDED,
        style=style,
        padding=(0, 1)
    ))
    console.print()

def display_key_value_pairs(data, title="Details", style="cyan"):
    """Display key-value pairs in a formatted panel"""
    if not data:
        console.print(f"[dim]{title}: (empty)[/dim]")
        return
    
    content = "\n".join(f"{key}: {value}" for key, value in data.items())
    console.print(Panel(
        Text(content, style="white"),
        title=title,
        box=box.ROUNDED,
        style=style,
        padding=(0, 1)
    ))
    console.print()

def confirm(message, default=True):
    """Get yes/no confirmation from user"""
    return Prompt.ask(
        f"[yellow]{message}[/yellow]",
        choices=["y", "n"],
        default="y" if default else "n",
        console=console
    ).lower() == "y"