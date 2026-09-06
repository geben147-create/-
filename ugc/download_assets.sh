#!/usr/bin/env bash
# 9 clips + 9 stills into ./clips and ./images. Run on YOUR machine
# (this repo's build container cannot reach the Pollo CDN).
set -e; mkdir -p clips images
C="https://videocdn.pollo.ai/web-cdn/pollo/production/cmf20asu60gslb2k5fhlac2gn/ori"
curl -fsSL "$C/1788664959984-2dd3f302-7af5-4056-9e48-e98530cb122c.mp4" -o clips/S1.mp4  && echo "clips/S1.mp4"
curl -fsSL "$C/1788665142075-e27a2140-f862-4c03-ae41-c436c36041a2.mp4" -o clips/S2.mp4  && echo "clips/S2.mp4"
curl -fsSL "$C/1788665199182-d70ed5b0-5269-4f5f-880c-08d05c5abccb.mp4" -o clips/S3.mp4  && echo "clips/S3.mp4"
curl -fsSL "$C/1788665161845-c0e959c0-02c1-4eba-946f-f8379dbd2f90.mp4" -o clips/S4.mp4  && echo "clips/S4.mp4"
curl -fsSL "$C/1788664956658-8faf84a8-5c17-4d27-819b-964b2683fc72.mp4" -o clips/S5.mp4  && echo "clips/S5.mp4"
curl -fsSL "$C/1788665305554-d250c7da-0ba7-4034-848c-c3e9d5499265.mp4" -o clips/S6.mp4  && echo "clips/S6.mp4"
curl -fsSL "$C/1788665171528-9f22fe72-192a-42bc-91e3-cbe7c0bc94be.mp4" -o clips/S7.mp4  && echo "clips/S7.mp4"
curl -fsSL "$C/1788665177688-efa95890-c075-45d4-9689-f99e6d2081a5.mp4" -o clips/S8.mp4  && echo "clips/S8.mp4"
curl -fsSL "$C/1788665181762-96faa563-cfc7-4fa0-85a1-27b757441201.mp4" -o clips/S9.mp4  && echo "clips/S9.mp4"
curl -fsSL "$C/1788663533262-47d73864-c33c-47f3-94c0-cd4014f51b3f.png" -o images/S1.png && echo "images/S1.png"
curl -fsSL "$C/1788663649436-5a58156d-f5f7-452a-8f45-335f48d72050.png" -o images/S2.png && echo "images/S2.png"
curl -fsSL "$C/cmtp85ee52innu51rrqx3hlhg-0-311393d345114420.png" -o images/S3.png && echo "images/S3.png"
curl -fsSL "$C/1788663658612-1de9a19b-6996-47b7-9c91-7ef37b174da1.png" -o images/S4.png && echo "images/S4.png"
curl -fsSL "$C/1788663662622-a09a4a8d-de8d-43ac-a17c-9b196330d090.png" -o images/S5.png && echo "images/S5.png"
curl -fsSL "$C/1788663785765-d10e34c7-87b8-44cc-a729-67860c04f8de.png" -o images/S6.png && echo "images/S6.png"
curl -fsSL "$C/1788663790092-c5042c44-0b55-4056-b49e-52dfba5e9b4c.png" -o images/S7.png && echo "images/S7.png"
curl -fsSL "$C/1788663792525-be375ceb-f033-4140-8867-f006bc27e009.png" -o images/S8.png && echo "images/S8.png"
curl -fsSL "$C/1788663642897-b5825dbe-e5fa-4081-8f11-0e8b637e8310.png" -o images/S9.png && echo "images/S9.png"
echo; echo "받았으면:  python build_video.py"
