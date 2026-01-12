#!/bin/bash
# Split Jackson's "Social and Economic Networks" into chapter PDFs
# Page numbers adjusted: PDF page = book page + 1 (due to front matter)

# Don't exit on qpdf warnings (exit code 3 = warnings but success)
set -o pipefail

SOURCE="references/Social and Economic Networks.pdf"
OUTDIR="references/jackson-social-economic-networks"

if [ ! -f "$SOURCE" ]; then
    echo "Error: Source PDF not found: $SOURCE"
    exit 1
fi

if ! command -v qpdf &> /dev/null; then
    echo "Error: qpdf not installed. Install with: sudo pacman -S qpdf"
    exit 1
fi

mkdir -p "$OUTDIR"

echo "Splitting Jackson PDF into chapters..."

# Chapter page ranges (book pages + 1 for PDF offset)
# Book TOC: Ch1=17, Ch2=39, Ch3=83, Ch4=107, Ch5=167, Ch6=201, Ch7=239,
#           Ch8=287, Ch9=333, Ch10=423, Ch11=479, Ch12=531, Ch13=561

qpdf "$SOURCE" --pages . 18-39 -- "$OUTDIR/01-introduction.pdf"
echo "  Created 01-introduction.pdf"

qpdf "$SOURCE" --pages . 40-83 -- "$OUTDIR/02-representing-measuring-networks.pdf"
echo "  Created 02-representing-measuring-networks.pdf"

qpdf "$SOURCE" --pages . 84-107 -- "$OUTDIR/03-empirical-background.pdf"
echo "  Created 03-empirical-background.pdf"

qpdf "$SOURCE" --pages . 108-167 -- "$OUTDIR/04-random-graph-models.pdf"
echo "  Created 04-random-graph-models.pdf"

qpdf "$SOURCE" --pages . 168-201 -- "$OUTDIR/05-growing-random-networks.pdf"
echo "  Created 05-growing-random-networks.pdf"

qpdf "$SOURCE" --pages . 202-239 -- "$OUTDIR/06-strategic-network-formation.pdf"
echo "  Created 06-strategic-network-formation.pdf"

qpdf "$SOURCE" --pages . 240-287 -- "$OUTDIR/07-diffusion-through-networks.pdf"
echo "  Created 07-diffusion-through-networks.pdf"

qpdf "$SOURCE" --pages . 288-333 -- "$OUTDIR/08-learning-and-networks.pdf"
echo "  Created 08-learning-and-networks.pdf"

qpdf "$SOURCE" --pages . 334-423 -- "$OUTDIR/09-decisions-behavior-games.pdf"
echo "  Created 09-decisions-behavior-games.pdf"

qpdf "$SOURCE" --pages . 424-479 -- "$OUTDIR/10-networked-markets.pdf"
echo "  Created 10-networked-markets.pdf"

qpdf "$SOURCE" --pages . 480-531 -- "$OUTDIR/11-game-theoretic-network-formation.pdf"
echo "  Created 11-game-theoretic-network-formation.pdf"

qpdf "$SOURCE" --pages . 532-561 -- "$OUTDIR/12-allocation-rules-cooperative-games.pdf"
echo "  Created 12-allocation-rules-cooperative-games.pdf"

qpdf "$SOURCE" --pages . 562-593 -- "$OUTDIR/13-observing-measuring-social-interaction.pdf"
echo "  Created 13-observing-measuring-social-interaction.pdf"

echo ""
echo "Done. Chapters extracted to: $OUTDIR"
ls -la "$OUTDIR"
