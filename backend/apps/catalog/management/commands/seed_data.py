"""Load the 6 categories and 24 sample products.

    python manage.py seed_data

Safe to run more than once: existing categories/products (matched by name/SKU)
are left untouched, so your own edits in the admin are never overwritten.
Placeholder product images are drawn locally with Pillow (no internet needed);
replace them with real photos from the admin whenever you like.
"""
import textwrap
from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image, ImageDraw, ImageFont

from apps.catalog.models import Category, Product, ProductImage

# name -> (description, background colour, text colour)
CATEGORIES = {
    "Educational": ("Toys that build skills through play.", "#DBEAFE", "#1E3A8A"),
    "Dolls": ("Dolls, dollhouses and imaginative play.", "#FCE7F3", "#831843"),
    "Cars": ("Cars, trucks and trains of every size.", "#FEE2E2", "#7F1D1D"),
    "Action Figures": ("Heroes, robots and adventure playsets.", "#EDE9FE", "#4C1D95"),
    "Board Games": ("Games for family nights and friendly rivalry.", "#FEF3C7", "#78350F"),
    "Building Toys": ("Bricks, tiles and construction sets.", "#DCFCE7", "#14532D"),
}

# (category, sku, name, brand, price, discount %, stock, age_min, age_max, featured, short, description)
PRODUCTS = [
    # ---- Educational
    ("Educational", "EDU-001", "Alphabet Learning Blocks", "BrightSteps", "24.99", 0, 40, 2, 5, True,
     "48 wooden letter and number blocks.",
     "Chunky wooden blocks with letters, numbers and pictures help toddlers learn to spell and count while stacking. Smooth, non-toxic finish."),
    ("Educational", "EDU-002", "Junior Science Lab Kit", "Curio Labs", "39.99", 15, 25, 6, 12, True,
     "20 safe experiments for young scientists.",
     "Grow crystals, build a volcano and explore magnetism with 20 guided experiments. Includes safety goggles, tools and a full-colour manual."),
    ("Educational", "EDU-003", "Solar System Floor Puzzle", "BrightSteps", "18.99", 0, 60, 4, 8, False,
     "100-piece giant puzzle with planet facts.",
     "A 100-piece floor puzzle that shows the planets in order, with a fun fact printed on each piece. Finished size is about 90 x 60 cm."),
    ("Educational", "EDU-004", "Coding Robot Starter Kit", "Curio Labs", "79.99", 20, 12, 8, 14, False,
     "Build and program your own robot.",
     "Snap together a working robot and program it with simple drag-and-drop commands. Teaches sequencing, loops and problem solving."),
    # ---- Dolls
    ("Dolls", "DOL-001", "Classic Rag Doll", "Petal & Pine", "22.99", 0, 35, 2, 8, False,
     "Soft cuddly doll with woollen hair.",
     "A cuddly rag doll with an embroidered face and a removable cotton dress. Machine washable and gentle enough for toddlers."),
    ("Dolls", "DOL-002", "Dream Dollhouse", "Petal & Pine", "129.99", 10, 8, 4, 10, True,
     "3-storey wooden dollhouse with 20 furniture pieces.",
     "A three-storey wooden dollhouse with opening doors, a staircase and twenty pieces of furniture. Assembly required (about 45 minutes)."),
    ("Dolls", "DOL-003", "Baby Care Doll Set", "Petal & Pine", "34.99", 0, 3, 3, 7, False,
     "Soft-bodied baby doll with bottle and blanket.",
     "A soft-bodied baby doll with a feeding bottle, blanket and rattle. Encourages caring, role play and storytelling."),
    ("Dolls", "DOL-004", "Fashion Designer Doll Studio", "Petal & Pine", "44.99", 25, 20, 6, 12, False,
     "Doll with 30 mix-and-match outfit pieces.",
     "Design and swap outfits with 30 clothing and accessory pieces. Includes a poseable doll, a sketch pad and a fold-out runway."),
    # ---- Cars
    ("Cars", "CAR-001", "Remote Control Off-Road Truck", "TurboTrail", "59.99", 15, 18, 6, 14, True,
     "Rechargeable 4x4 truck with 2.4 GHz remote.",
     "A rugged 4x4 truck with rubber tyres and independent suspension. Includes a rechargeable battery and up to 30 minutes of play per charge."),
    ("Cars", "CAR-002", "Die-Cast Racing Car Set (6 Pack)", "TurboTrail", "19.99", 0, 70, 3, None, False,
     "Six collectible metal race cars.",
     "Six detailed die-cast race cars with free-rolling wheels. Great for racing on floors, tracks and tabletops."),
    ("Cars", "CAR-003", "Pull-Back Fire Truck", "TurboTrail", "14.99", 0, 0, 3, 6, False,
     "Pull back, release and watch it go.",
     "A sturdy fire truck with a pull-back motor, extendable ladder and working siren button. Requires 2 AAA batteries (not included)."),
    ("Cars", "CAR-004", "Wooden Train Track Set", "TurboTrail", "49.99", 10, 22, 3, 8, False,
     "60-piece wooden railway with two trains.",
     "A 60-piece wooden railway with bridges, tunnels and two magnetic trains. Compatible with most major wooden track brands."),
    # ---- Action Figures
    ("Action Figures", "ACT-001", "Galaxy Defender Figure", "HeroForge", "16.99", 0, 45, 4, 12, False,
     "12 cm poseable figure with 3 accessories.",
     "A 12 cm poseable space hero with a removable helmet, blaster and shield. Bends at the arms, legs and neck."),
    ("Action Figures", "ACT-002", "Robo Knight Articulated Figure", "HeroForge", "27.99", 20, 30, 6, 14, True,
     "Collectible figure with 18 points of articulation.",
     "A 18 cm armoured robot knight with 18 points of articulation, a glowing sword and interchangeable hands."),
    ("Action Figures", "ACT-003", "Jungle Rescue Team (5 Figures)", "HeroForge", "32.99", 0, 15, 4, 10, False,
     "Five explorer figures with gear.",
     "Five jungle explorer figures with binoculars, ropes and a rescue stretcher. Perfect for outdoor adventures and imaginative play."),
    ("Action Figures", "ACT-004", "Dino Hunter Playset", "HeroForge", "45.99", 30, 10, 5, 12, False,
     "Figure, off-road vehicle and a roaring dinosaur.",
     "A ranger figure, an off-road buggy and a large dinosaur with moving jaws. Includes a net launcher and a habitat backdrop."),
    # ---- Board Games
    ("Board Games", "BRD-001", "Family Trivia Night", "PlayHaus", "29.99", 0, 50, 8, None, True,
     "1,000 questions for 2-8 players.",
     "Test your knowledge across six categories with 1,000 questions for all ages. Includes a game board, timer and scoring pegs."),
    ("Board Games", "BRD-002", "Treasure Island Strategy Game", "PlayHaus", "34.99", 10, 28, 8, None, False,
     "Build the map and race to find the treasure.",
     "Players build the island as they explore, racing rivals to dig up the hidden treasure. A game takes about 40 minutes."),
    ("Board Games", "BRD-003", "Word Detective Card Game", "PlayHaus", "12.99", 0, 80, 7, None, False,
     "Quick vocabulary card game for 2-6 players.",
     "Solve word clues faster than your rivals in this pocket-sized card game. Easy to learn and perfect for travel."),
    ("Board Games", "BRD-004", "Memory Match Junior", "PlayHaus", "15.99", 0, 4, 3, 6, False,
     "Picture-matching game with 36 large cards.",
     "Flip and find matching pairs among 36 thick, colourful picture cards. Builds memory and concentration."),
    # ---- Building Toys
    ("Building Toys", "BLD-001", "Classic Bricks Box (500 pieces)", "BrickWorks", "34.99", 15, 55, 4, None, True,
     "500 colourful bricks and a building guide.",
     "Five hundred bricks in twelve colours, plus windows, doors and wheels. Compatible with major brick brands."),
    ("Building Toys", "BLD-002", "Magnetic Tile Builder Set (60 pcs)", "BrickWorks", "44.99", 0, 26, 3, 10, True,
     "60 magnetic tiles that snap together.",
     "Sixty translucent magnetic tiles in geometric shapes for building towers, houses and castles. Strong enclosed magnets for safe play."),
    ("Building Toys", "BLD-003", "City Builder Set (300 pcs)", "BrickWorks", "39.99", 20, 17, 6, 12, False,
     "Build a bustling city with cars and buildings.",
     "Three hundred pieces to build a fire station, shop and two vehicles, with three mini figures included."),
    ("Building Toys", "BLD-004", "Marble Run Construction Set", "BrickWorks", "36.99", 0, 33, 5, 12, False,
     "85-piece track set with 30 marbles.",
     "Design your own twisting marble run with 85 track pieces and 30 glass marbles. Every layout works differently."),
]


def _font(size):
    try:  # Pillow 10.1+ ships a scalable default font
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow: fixed-size fallback
        return ImageFont.load_default()


def make_placeholder(title, category_name, bg, fg):
    """Draw an 800x800 card with the product name; returns PNG bytes."""
    img = Image.new("RGB", (800, 800), bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 40, 760, 760], outline=fg, width=4)
    text = "\n".join(textwrap.wrap(title, 16))
    draw.multiline_text((400, 380), text, font=_font(56), fill=fg,
                        anchor="mm", align="center", spacing=14)
    draw.text((400, 700), category_name.upper(), font=_font(28), fill=fg, anchor="mm")
    buffer = BytesIO()
    img.save(buffer, "PNG")
    return buffer.getvalue()


class Command(BaseCommand):
    help = "Load 6 categories and 24 sample toys (safe to run repeatedly)."

    @transaction.atomic
    def handle(self, *args, **options):
        categories = {}
        new_categories = 0
        for order, (name, (desc, _bg, _fg)) in enumerate(CATEGORIES.items(), start=1):
            cat, created = Category.objects.get_or_create(
                name=name, defaults={"description": desc, "sort_order": order}
            )
            categories[name] = cat
            new_categories += created

        new_products = new_images = 0
        for (cat_name, sku, name, brand, price, discount, stock, age_min, age_max,
             featured, short, desc) in PRODUCTS:
            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults=dict(
                    category=categories[cat_name], name=name, brand=brand,
                    price=Decimal(price), discount_percent=discount, stock=stock,
                    age_min=age_min, age_max=age_max, is_featured=featured,
                    short_description=short, description=desc,
                ),
            )
            new_products += created
            if not product.images.exists():
                _desc, bg, fg = CATEGORIES[cat_name]
                image = ProductImage(product=product, alt_text=name, is_primary=True)
                image.image.save(
                    f"{product.slug}.png",
                    ContentFile(make_placeholder(name, cat_name, bg, fg)),
                    save=True,
                )
                new_images += 1

        if options["verbosity"] == 0:
            return
        self.stdout.write(self.style.SUCCESS(
            f"Done. New: {new_categories} categories, {new_products} products, "
            f"{new_images} images. Totals: {Category.objects.count()} categories, "
            f"{Product.objects.count()} products."
        ))