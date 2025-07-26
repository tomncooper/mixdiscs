import logging

from datetime import timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from mixdiscer.main import ProcessedPlaylist

LOG = logging.getLogger(__name__)

DEFAULT_TEMPLATE_DIR = Path("templates")


def duration_format(duration: timedelta) -> str:
    """Convert timedelta to MM:SS format"""
    total_seconds = int(duration.total_seconds())
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}"


def render_output(
        processed_playlists: list[ProcessedPlaylist],
        output_dir: Path,
        template_dir: Path = DEFAULT_TEMPLATE_DIR,
) -> None:
    """ Render the processed playlists to HTML using Jinja2 template """

    LOG.info("Rendering HTML output to %s", output_dir)

    # Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader(template_dir))

    # Add custom filter
    env.filters['duration_format'] = duration_format

    # Load the template
    template = env.get_template("index.html.j2")

    # Render the template with the data
    html_content = template.render(processed_playlists=processed_playlists)

    # Write the rendered HTML to file
    output_file = output_dir.joinpath("index.html")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    LOG.info("HTML output successfully written to %s", output_file)
