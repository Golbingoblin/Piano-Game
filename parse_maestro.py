#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAESTRO Dataset Parser
CSV를 파싱하여 작곡가별 곡 목록을 JSON으로 저장
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

def parse_maestro_csv():
    """MAESTRO CSV를 파싱하여 작곡가별 곡 목록 생성"""
    maestro_csv = Path(__file__).parent / 'maestro-v3.0.0' / 'maestro-v3.0.0.csv'

    # 작곡가별 곡 데이터 저장
    composers = defaultdict(list)

    with open(maestro_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            composer = row['canonical_composer']
            title = row['canonical_title']
            midi_file = row['midi_filename']
            duration = float(row['duration'])
            year = row['year']

            composers[composer].append({
                'title': title,
                'midi_file': midi_file,
                'duration': duration,
                'year': year
            })

    # 작곡가 목록 생성 (알파벳 순 정렬)
    composer_data = {}
    for composer in sorted(composers.keys()):
        composer_data[composer] = {
            'name': composer,
            'pieces': composers[composer],
            'piece_count': len(composers[composer])
        }

    # JSON 저장
    output_path = Path(__file__).parent / 'web_app' / 'static' / 'data' / 'composers.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(composer_data, f, ensure_ascii=False, indent=2)

    print(f"[OK] Parsed {len(composer_data)} composers")
    print(f"[OK] Total pieces: {sum(len(v['pieces']) for v in composer_data.values())}")
    print(f"[OK] Saved to: {output_path}")

    # 작곡가 목록 출력
    print("\n작곡가 목록:")
    for composer, data in composer_data.items():
        print(f"  - {composer}: {data['piece_count']} pieces")

if __name__ == '__main__':
    parse_maestro_csv()
