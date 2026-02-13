# SEO Setup Instructions for BharatBuild AI

## Quick Setup Checklist

- [ ] Convert SVG images to PNG
- [ ] Set up Google Analytics 4
- [ ] Verify site in Google Search Console
- [ ] Import Google Ads keywords
- [ ] Deploy and submit sitemap

---

## 1. OG Images Setup

### Convert SVGs to PNG

The OG images are created as SVGs in `/frontend/public/`. You need to convert them to PNG:

**Option A: Using Online Converter**
1. Open `og-image.svg` in browser
2. Use https://svgtopng.com/ to convert
3. Ensure output is 1200x630px
4. Save as `og-image.png`
5. Repeat for `twitter-image.svg` (1200x600px)

**Option B: Using ImageMagick (CLI)**
```bash
# Install ImageMagick first
convert og-image.svg -resize 1200x630 og-image.png
convert twitter-image.svg -resize 1200x600 twitter-image.png
```

**Option C: Using Sharp (Node.js)**
```javascript
const sharp = require('sharp');

sharp('og-image.svg')
  .resize(1200, 630)
  .png()
  .toFile('og-image.png');
```

### Verify Images
After conversion, verify images appear correctly:
1. Deploy to staging
2. Use https://www.opengraph.xyz/ to test
3. Use Twitter Card Validator: https://cards-dev.twitter.com/validator

---

## 2. Google Analytics 4 Setup

### Step 1: Create GA4 Property
1. Go to https://analytics.google.com
2. Click "Admin" (gear icon)
3. Click "Create Property"
4. Enter property name: "BharatBuild AI"
5. Select your country and timezone
6. Click "Create"

### Step 2: Create Data Stream
1. In Admin > Data Streams, click "Add stream"
2. Select "Web"
3. Enter website URL: `bharatbuild.ai`
4. Enter stream name: "BharatBuild Web"
5. Click "Create stream"

### Step 3: Get Measurement ID
1. In the data stream, find "Measurement ID"
2. It starts with `G-` (e.g., `G-ABC123XYZ`)
3. Copy this ID

### Step 4: Add to Environment
```bash
# In .env.local
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-ABC123XYZ
```

### Step 5: Verify Tracking
1. Deploy the application
2. Go to GA4 > Reports > Realtime
3. Visit your website
4. You should see yourself as an active user

### Configure Events (Optional but Recommended)
In GA4 Admin:
1. Go to Events
2. Enable enhanced measurement
3. Configure conversions:
   - sign_up
   - payment_completed
   - project_generated

---

## 3. Google Search Console Setup

### Step 1: Add Property
1. Go to https://search.google.com/search-console
2. Click "Add property"
3. Choose "URL prefix" method
4. Enter: `https://bharatbuild.ai`
5. Click "Continue"

### Step 2: Verify Ownership
1. Choose "HTML tag" method
2. Copy the meta tag content (just the code, not the full tag)
   - Example: `<meta name="google-site-verification" content="YOUR_CODE" />`
   - Copy only: `YOUR_CODE`
3. Add to .env.local:
```bash
NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION=YOUR_CODE
```
4. Deploy the changes
5. Return to Search Console and click "Verify"

### Step 3: Submit Sitemap
1. In Search Console, go to "Sitemaps"
2. Enter: `sitemap.xml`
3. Click "Submit"
4. Wait for Google to process (usually 24-48 hours)

### Step 4: Request Indexing
1. Go to URL Inspection
2. Enter your homepage URL
3. Click "Request Indexing"
4. Repeat for important pages:
   - /pricing
   - /register
   - /showcase
   - /campus-drive

---

## 4. Google Ads Setup

### Import Keywords
1. Go to https://ads.google.com
2. Create a new campaign
3. Go to Tools > Keyword Planner
4. Click "Upload keyword file"
5. Upload `seo/google-ads-keyword-groups.csv`

### Campaign Structure
The CSV is organized into campaigns:
- **Student Projects** - Target students searching for projects
- **AI Code Generator** - Brand awareness
- **Framework Specific** - React, Next.js, Python developers
- **Mobile Apps** - Flutter, React Native
- **Competitor Keywords** - Bolt, v0, Copilot alternatives
- **Startup MVP** - Founder-focused keywords
- **Campus Placement** - College recruitment
- **India Specific** - Made in India, regional universities

### Budget Recommendations
| Campaign | Daily Budget (INR) | Priority |
|----------|-------------------|----------|
| Student Projects | ₹500-1000 | High |
| AI Code Generator | ₹300-500 | High |
| Competitor Keywords | ₹200-400 | Medium |
| Startup MVP | ₹200-300 | Medium |
| Campus Placement | ₹100-200 | Low |

### Conversion Tracking
1. In Google Ads, go to Tools > Conversions
2. Create conversions for:
   - Sign ups
   - Payments
   - Project generations
3. Use the `analytics.trackConversion()` function in code

---

## 5. Blog Deployment

### Blog Posts Created
Five SEO-optimized blog posts are in `seo/blog-posts/`:
1. `01-complete-final-year-project-with-ai.md`
2. `02-ieee-format-project-report-guide.md`
3. `03-ai-code-generators-compared.md`
4. `04-build-mvp-without-coding.md`
5. `05-50-final-year-project-ideas-cse.md`

### Publishing Options

**Option A: Create /blog route in Next.js**
1. Create `app/blog/page.tsx` for blog listing
2. Create `app/blog/[slug]/page.tsx` for posts
3. Parse markdown files with `gray-matter` and `remark`

**Option B: Use Hashnode/Dev.to**
1. Create account on Hashnode
2. Map custom domain (blog.bharatbuild.ai)
3. Publish markdown content

**Option C: WordPress/Ghost**
1. Set up WordPress/Ghost at blog.bharatbuild.ai
2. Import markdown posts
3. Configure SEO plugins

---

## 6. Additional SEO Tasks

### Create OG Images for Blog Posts
Each blog post should have unique OG image:
- Include post title
- Include BharatBuild branding
- Size: 1200x630px

### Internal Linking
Add links between:
- Homepage → Blog posts
- Blog posts → Build page
- Blog posts → Related posts

### Backlink Building
1. Submit to directories:
   - Product Hunt
   - BetaList
   - Indie Hackers
   - StartupBase

2. Guest posting:
   - Dev.to
   - Medium
   - Tech blogs

3. Social media:
   - Share blog posts on LinkedIn
   - Twitter threads
   - Reddit (r/India, r/csMajors)

---

## File Summary

```
BharatBuild_AI/
├── seo/
│   ├── keywords.csv                    # 100+ keywords
│   ├── google-ads-keyword-groups.csv   # Google Ads ready
│   ├── seo-content.md                  # Marketing copy
│   ├── SETUP_INSTRUCTIONS.md           # This file
│   └── blog-posts/
│       ├── 01-complete-final-year-project-with-ai.md
│       ├── 02-ieee-format-project-report-guide.md
│       ├── 03-ai-code-generators-compared.md
│       ├── 04-build-mvp-without-coding.md
│       └── 05-50-final-year-project-ideas-cse.md
│
├── frontend/
│   ├── .env.example                    # Environment template
│   ├── public/
│   │   ├── og-image.svg               # Convert to PNG!
│   │   └── twitter-image.svg          # Convert to PNG!
│   └── src/
│       ├── app/
│       │   ├── layout.tsx             # SEO metadata + GA
│       │   ├── sitemap.ts             # Dynamic sitemap
│       │   ├── robots.ts              # Robots.txt
│       │   └── [pages]/layout.tsx     # Page-specific SEO
│       └── components/
│           ├── seo/JsonLd.tsx         # Structured data
│           └── analytics/GoogleAnalytics.tsx
```

---

## Support

For questions, contact: info@bharatbuild.ai
