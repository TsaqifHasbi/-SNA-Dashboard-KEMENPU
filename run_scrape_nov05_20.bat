@echo off
chcp 65001 >nul
title Scraper Kemen PU (5 - 20 November 2026)

if "%1"=="" (
    python run_scrape_nov05_20.py
) else (
    python run_scrape_nov05_20.py %1
)

pause
