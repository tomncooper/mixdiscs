import logging
import shutil

from datetime import timedelta
from pathlib import Path
from collections import defaultdict
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from mixdiscer.music_service import ProcessedPlaylist

LOG = logging.getLogger(__name__)

DEFAULT_TEMPLATE_DIR = Path("templates")
PLAYLISTS_PER_PAGE = 20
RECENT_PLAYLISTS_COUNT = 10


def duration_format(duration: timedelta) -> str:
    """Convert timedelta to MM:SS format"""
    total_seconds = int(duration.total_seconds())
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}"


def get_file_modified_time(processed_playlist: ProcessedPlaylist) -> float:
    """Get the modification time of the playlist file"""
    if processed_playlist.user_playlist.filepath:
        return processed_playlist.user_playlist.filepath.stat().st_mtime
    return 0


def paginate(items: list, page_size: int) -> list[list]:
    """Split items into pages"""
    return [items[i:i + page_size] for i in range(0, len(items), page_size)]


def create_pagination_info(current_page: int, total_pages: int, base_filename: str) -> dict:
    """Create pagination information for template"""
    if total_pages <= 1:
        return None
    
    # Show up to 5 page numbers at a time
    page_window = 2
    start_page = max(1, current_page - page_window)
    end_page = min(total_pages, current_page + page_window)
    
    pages = list(range(start_page, end_page + 1))
    
    page_links = {}
    for page_num in range(1, total_pages + 1):
        if page_num == 1:
            page_links[page_num] = f"{base_filename}.html"
        else:
            page_links[page_num] = f"{base_filename}-page{page_num}.html"
    
    prev_page = None
    if current_page > 1:
        prev_page = page_links[current_page - 1]
    
    next_page = None
    if current_page < total_pages:
        next_page = page_links[current_page + 1]
    
    return {
        'current_page': current_page,
        'total_pages': total_pages,
        'pages': pages,
        'page_links': page_links,
        'prev_page': prev_page,
        'next_page': next_page,
    }


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

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy CSS and JS files to output directory
    for static_file in ['style.css', 'script.js']:
        src_file = template_dir / static_file
        if src_file.exists():
            dst_file = output_dir / static_file
            shutil.copy2(src_file, dst_file)
            LOG.info("Copied %s to output directory", static_file)
    
    # Sort playlists by modification time (most recent first)
    sorted_playlists = sorted(
        processed_playlists,
        key=get_file_modified_time,
        reverse=True
    )
    
    # Render main index page (10 most recent playlists)
    recent_playlists = sorted_playlists[:RECENT_PLAYLISTS_COUNT]
    template = env.get_template("index.html.j2")
    html_content = template.render(
        processed_playlists=recent_playlists,
        show_all_link=False,
        page_title=f"Recently Updated Playlists"
    )
    
    output_file = output_dir / "index.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    LOG.info("Main index page written to %s", output_file)
    
    # Render paginated all-playlists page
    pages = paginate(sorted_playlists, PLAYLISTS_PER_PAGE)
    for page_num, page_playlists in enumerate(pages, start=1):
        pagination_info = create_pagination_info(page_num, len(pages), "all-playlists")
        html_content = template.render(
            processed_playlists=page_playlists,
            show_all_link=True,
            page_title=f"All Playlists (Page {page_num} of {len(pages)})",
            pagination=pagination_info
        )
        
        if page_num == 1:
            output_file = output_dir / "all-playlists.html"
        else:
            output_file = output_dir / f"all-playlists-page{page_num}.html"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        LOG.info("All-playlists page %d written to %s", page_num, output_file)
    
    # Collect users and genres
    users = defaultdict(list)
    genres = defaultdict(list)
    
    for playlist in processed_playlists:
        users[playlist.user_playlist.user].append(playlist)
        genres[playlist.user_playlist.genre].append(playlist)
    
    # Render user pages
    for user, user_playlists in users.items():
        user_playlists_sorted = sorted(user_playlists, key=get_file_modified_time, reverse=True)
        html_content = template.render(
            processed_playlists=user_playlists_sorted,
            show_all_link=True,
            page_title=f"Playlists by {user}"
        )
        
        output_file = output_dir / f"user-{user}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        LOG.info("User page for %s written to %s", user, output_file)
    
    # Render genre pages
    for genre, genre_playlists in genres.items():
        genre_playlists_sorted = sorted(genre_playlists, key=get_file_modified_time, reverse=True)
        html_content = template.render(
            processed_playlists=genre_playlists_sorted,
            show_all_link=True,
            page_title=f"Playlists in {genre.title()}"
        )
        
        output_file = output_dir / f"genre-{genre}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        LOG.info("Genre page for %s written to %s", genre, output_file)
    
    # Render users index page
    users_template = env.get_template("users.html.j2")
    users_list = sorted([(user, len(playlists)) for user, playlists in users.items()])
    html_content = users_template.render(users=users_list)
    
    output_file = output_dir / "users.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    LOG.info("Users index page written to %s", output_file)
    
    # Render genres index page
    genres_template = env.get_template("genres.html.j2")
    genres_list = sorted([(genre, len(playlists)) for genre, playlists in genres.items()])
    html_content = genres_template.render(genres=genres_list)
    
    output_file = output_dir / "genres.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    LOG.info("Genres index page written to %s", output_file)

    LOG.info("HTML output successfully rendered with %d playlists", len(processed_playlists))

