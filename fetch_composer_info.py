#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wikipedia API를 통해 작곡가 정보 및 이미지 수집
"""

import json
import requests
import time
from pathlib import Path
from urllib.parse import quote

def fetch_wikipedia_info(composer_name):
    """Wikipedia API로 작곡가 정보 가져오기"""
    # Wikipedia API 엔드포인트
    base_url = "https://en.wikipedia.org/w/api.php"

    # User-Agent 헤더 추가
    headers = {
        'User-Agent': 'ClassicalMusicLibrary/1.0 (Educational Project)'
    }

    # 1. 검색하여 정확한 페이지 찾기
    search_params = {
        'action': 'query',
        'format': 'json',
        'list': 'search',
        'srsearch': composer_name + ' composer',
        'srlimit': 1
    }

    try:
        response = requests.get(base_url, params=search_params, headers=headers, timeout=10)
        data = response.json()

        if not data.get('query', {}).get('search'):
            print("  [SKIP] No Wikipedia page found")
            return None

        page_title = data['query']['search'][0]['title']

        # 2. 페이지 상세 정보 가져오기 (요약 + 이미지)
        page_params = {
            'action': 'query',
            'format': 'json',
            'titles': page_title,
            'prop': 'extracts|pageimages',
            'exintro': True,
            'explaintext': True,
            'pithumbsize': 300,
            'redirects': 1
        }

        response = requests.get(base_url, params=page_params, headers=headers, timeout=10)
        data = response.json()

        pages = data.get('query', {}).get('pages', {})
        page = next(iter(pages.values()))

        # 추출된 정보
        info = {
            'name': composer_name,
            'wikipedia_title': page_title,
            'extract': page.get('extract', '').split('\n')[0][:500],  # 첫 문단 500자
            'image_url': page.get('thumbnail', {}).get('source', ''),
            'image_width': page.get('thumbnail', {}).get('width', 0),
            'image_height': page.get('thumbnail', {}).get('height', 0)
        }

        try:
            print(f"  [OK] {composer_name}")
        except UnicodeEncodeError:
            print("  [OK]")
        return info

    except Exception as e:
        try:
            print(f"  [ERROR] {composer_name}: {e}")
        except UnicodeEncodeError:
            print(f"  [ERROR]: {e}")
        return None


def main():
    """모든 작곡가의 Wikipedia 정보 수집"""
    # composers.json 로드
    composers_path = Path(__file__).parent / 'web_app' / 'static' / 'data' / 'composers.json'

    with open(composers_path, 'r', encoding='utf-8') as f:
        composers_data = json.load(f)

    print(f"Fetching Wikipedia info for {len(composers_data)} composers...\n")

    # 각 작곡가의 Wikipedia 정보 수집
    composer_info = {}
    for i, composer_name in enumerate(composers_data.keys(), 1):
        try:
            print(f"[{i}/{len(composers_data)}] {composer_name}")
        except UnicodeEncodeError:
            print(f"[{i}/{len(composers_data)}] [name encoding issue]")

        info = fetch_wikipedia_info(composer_name)

        if info:
            composer_info[composer_name] = info

        # API 요청 제한 고려하여 대기
        time.sleep(0.5)

    # 저장
    output_path = Path(__file__).parent / 'web_app' / 'static' / 'data' / 'composer_info.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(composer_info, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Saved {len(composer_info)} composer info to {output_path}")

if __name__ == '__main__':
    main()
