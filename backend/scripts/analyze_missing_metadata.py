import sys
import os
import json
import logging
from sqlalchemy import select, func

# Adjust path to import backend modules
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPTS_DIR)
sys.path.append(BACKEND_DIR)

from app.db import get_session, Listen

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("analyze_missing")

def main():
    try:
        getattr(sys.stdout, 'reconfigure')(encoding='utf-8')
    except AttributeError:
        pass # Not available in some environments
    session = get_session()
    try:
        logger.info("Querying database for tracks missing duration or album...")
        stmt = (
            select(Listen.artist, Listen.title, func.count(Listen.id).label("play_count"))
            .where((Listen.duration_secs.is_(None)) | (Listen.album.is_(None)))
            .group_by(Listen.artist, Listen.title)
            .order_by(func.count(Listen.id).desc())
        )
        results = session.execute(stmt).all()
        
        total_missing_tracks = len(results)
        total_missing_plays = sum(r.play_count for r in results)
        logger.info("Found %d unique tracks missing metadata (totaling %d plays)", total_missing_tracks, total_missing_plays)
        
        if not results:
            print("No tracks missing metadata found!")
            return
            
        # Check source distribution of missing metadata tracks
        logger.info("Analyzing source distribution...")
        stmt_src_missing = (
            select(Listen.source, func.count(Listen.id).label("count"))
            .where((Listen.duration_secs.is_(None)) | (Listen.album.is_(None)))
            .group_by(Listen.source)
        )
        src_missing = session.execute(stmt_src_missing).all()
        
        stmt_src_all = (
            select(Listen.source, func.count(Listen.id).label("count"))
            .group_by(Listen.source)
        )
        src_all = session.execute(stmt_src_all).all()

        print("\n--- SOURCE DISTRIBUTION FOR MISSING METADATA ---")
        for row in src_missing:
            print(f"Source: {row.source:15s} | Missing Plays: {row.count:6d}")
            
        print("\n--- SOURCE DISTRIBUTION FOR ALL TRACKS ---")
        for row in src_all:
            print(f"Source: {row.source:15s} | Total Plays:   {row.count:6d}")
        print("---------------------------------------------\n")
        
        print("\n--- TOP 50 MISSING TRACKS (BY PLAY COUNT) ---")
        for i, row in enumerate(results[:50]):
            print(f"{i+1:3d}. Plays: {row.play_count:4d} | Artist: {row.artist} | Title: {row.title}")
        print("---------------------------------------------\n")
        
        # Save full list to JSON
        output_file = os.path.join(SCRIPTS_DIR, "missing_tracks.json")
        data_to_save = [
            {"artist": row.artist, "title": row.title, "play_count": row.play_count}
            for row in results
        ]
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
            
        logger.info("Saved all %d missing tracks to %s", total_missing_tracks, output_file)
        
    finally:
        session.close()

if __name__ == "__main__":
    main()
