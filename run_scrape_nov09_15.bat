@echo off
chcp 65001 >nul
title Scraper Kemen PU (9 - 15 November 2026)

if "%1"=="" (
    python run_scrape_nov09_15.py
) else (
    python run_scrape_nov09_15.py %1
)

pause
