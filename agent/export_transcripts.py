"""
Export conversation transcripts in readable format.

This script reads the labs_call_evaluations.csv file and extracts
full conversation transcripts into separate readable text files.
"""

import csv
import json
import os
from pathlib import Path


def export_transcripts_to_txt():
    """Export all conversation transcripts from CSV to individual TXT files."""
    
    # Path to the CSV file
    csv_file = Path(__file__).parent / 'labs_evaluations' / 'labs_call_evaluations.csv'
    output_dir = Path(__file__).parent / 'labs_evaluations' / 'transcripts'
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    if not csv_file.exists():
        print(f"CSV file not found: {csv_file}")
        return
    
    print(f"Reading transcripts from: {csv_file}")
    print(f"Exporting to: {output_dir}")
    print("=" * 80)
    
    # Read CSV and extract transcripts
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            call_id = row.get('call_id', 'unknown')
            transcript_json = row.get('conversation_transcript', '')
            
            if not transcript_json:
                print(f"WARNING: No transcript for {call_id}")
                continue
            
            try:
                # Parse the JSON conversation
                conversation = json.loads(transcript_json)
                
                if not conversation:
                    print(f"WARNING: Empty transcript for {call_id}")
                    continue
                
                # Create a readable text file
                txt_file = output_dir / f"{call_id}_transcript.txt"
                
                with open(txt_file, 'w', encoding='utf-8') as out:
                    # Write header
                    out.write(f"Call ID: {call_id}\n")
                    out.write(f"Duration: {row.get('duration_seconds', 'N/A')} seconds\n")
                    out.write(f"Total Turns: {len(conversation)}\n")
                    out.write(f"User Sentiment: {row.get('user_sentiment', 'N/A')}\n")
                    out.write(f"Query Category: {row.get('query_category', 'N/A')}\n")
                    out.write("=" * 80 + "\n\n")
                    
                    # Write conversation
                    for i, turn in enumerate(conversation, 1):
                        role = turn.get('role', 'unknown').upper()
                        content = turn.get('content', '')
                        
                        out.write(f"[Turn {i}] {role}:\n")
                        out.write(f"{content}\n\n")
                    
                    # Write summary at the end
                    out.write("=" * 80 + "\n")
                    out.write(f"CALL SUMMARY:\n{row.get('call_summary', 'N/A')}\n\n")
                    out.write(f"Notes: {row.get('notes', 'N/A')}\n")
                
                print(f"OK: Exported: {txt_file.name} ({len(conversation)} turns)")
                
            except json.JSONDecodeError as e:
                print(f"ERROR: Error parsing transcript for {call_id}: {e}")
            except Exception as e:
                print(f"ERROR: Error exporting {call_id}: {e}")
    
    print("=" * 80)
    print(f"\nOK: Export complete! Check the '{output_dir.name}' folder.")


def export_all_transcripts_combined():
    """Export all transcripts into a single combined file."""
    
    csv_file = Path(__file__).parent / 'labs_evaluations' / 'labs_call_evaluations.csv'
    output_file = Path(__file__).parent / 'labs_evaluations' / 'all_transcripts_combined.txt'
    
    if not csv_file.exists():
        print(f"CSV file not found: {csv_file}")
        return
    
    print(f"Creating combined transcript file: {output_file}")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        with open(output_file, 'w', encoding='utf-8') as out:
            out.write("ALL CALL TRANSCRIPTS\n")
            out.write("=" * 80 + "\n\n")
            
            call_count = 0
            for row in reader:
                call_id = row.get('call_id', 'unknown')
                transcript_json = row.get('conversation_transcript', '')
                
                if not transcript_json:
                    continue
                
                try:
                    conversation = json.loads(transcript_json)
                    if not conversation:
                        continue
                    
                    call_count += 1
                    
                    # Write call header
                    out.write(f"\n{'#' * 80}\n")
                    out.write(f"CALL #{call_count}: {call_id}\n")
                    out.write(f"{'#' * 80}\n\n")
                    out.write(f"Duration: {row.get('duration_seconds', 'N/A')} seconds\n")
                    out.write(f"Total Turns: {len(conversation)}\n")
                    out.write(f"User Sentiment: {row.get('user_sentiment', 'N/A')}\n")
                    out.write(f"Query Category: {row.get('query_category', 'N/A')}\n")
                    out.write(f"Query Resolved: {row.get('query_resolved', 'N/A')}\n")
                    out.write("=" * 80 + "\n\n")
                    
                    # Write conversation
                    for i, turn in enumerate(conversation, 1):
                        role = turn.get('role', 'unknown').upper()
                        content = turn.get('content', '')
                        
                        out.write(f"[Turn {i}] {role}:\n")
                        out.write(f"{content}\n\n")
                    
                    # Write summary
                    out.write("-" * 80 + "\n")
                    out.write(f"SUMMARY: {row.get('call_summary', 'N/A')}\n")
                    out.write(f"NOTES: {row.get('notes', 'N/A')}\n")
                    out.write("-" * 80 + "\n\n")
                    
                except json.JSONDecodeError:
                    pass
                except Exception:
                    pass
            
            out.write(f"\n{'#' * 80}\n")
            out.write(f"Total calls with transcripts: {call_count}\n")
            out.write(f"{'#' * 80}\n")
    
    print(f"OK: Combined transcript file created: {output_file.name}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TRANSCRIPT EXPORT TOOL")
    print("=" * 80 + "\n")
    
    # Export individual transcript files
    export_transcripts_to_txt()
    
    print()
    
    # Export combined file
    export_all_transcripts_combined()
    
    print("\n" + "=" * 80)
    print("DONE!")
    print("=" * 80 + "\n")
