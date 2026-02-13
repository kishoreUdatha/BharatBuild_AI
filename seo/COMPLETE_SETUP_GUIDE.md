# BharatBuild AI - Complete SEO Setup Guide

## Quick Start Checklist

```
[ ] Step 1: Convert SVG images to PNG
[ ] Step 2: Set up Google Analytics 4
[ ] Step 3: Set up Google Search Console
[ ] Step 4: Import keywords to Google Ads
[ ] Step 5: Deploy and submit sitemap
[ ] Step 6: Blog is ready at /blog
```

---

## Step 1: Convert SVG Images to PNG

### Option A: Using the Script (Recommended)

```bash
# Navigate to frontend directory
cd frontend

# Install sharp
npm install sharp

# Run conversion script
node scripts/convert-images.js
```

### Option B: Online Conversion

1. Open `frontend/public/og-image.svg` in browser
2. Go to https://svgtopng.com/
3. Upload the SVG file
4. Set dimensions: **1200 x 630 px**
5. Download and save as `frontend/public/og-image.png`
6. Repeat for `twitter-image.svg` (1200 x 600 px)

### Option C: Using Figma

1. Open Figma
2. Import SVG file
3. Select the frame
4. Export as PNG at 2x scale
5. Resize to exact dimensions

### Verify Images Work

After converting:
1. Deploy to staging
2. Test at: https://www.opengraph.xyz/
3. Enter your URL and verify images appear

---

## Step 2: Set Up Google Analytics 4

### 2.1 Create Google Analytics Account

1. Go to https://analytics.google.com
2. Click **"Start measuring"** (or **Admin** if you have an account)
3. Click **"Create Property"**

### 2.2 Property Setup

```
Property name: BharatBuild AI
Reporting time zone: (GMT+05:30) India Standard Time
Currency: Indian Rupee (₹)
```

4. Click **"Next"**
5. Select industry: **Technology**
6. Select business size
7. Click **"Create"**

### 2.3 Create Web Data Stream

1. Select **"Web"** platform
2. Enter:
   - Website URL: `bharatbuild.ai`
   - Stream name: `BharatBuild Web`
3. Click **"Create stream"**

### 2.4 Get Your Measurement ID

1. In the stream details, find **"Measurement ID"**
2. It looks like: `G-ABC123XYZ`
3. **Copy this ID**

### 2.5 Add to Your Project

Create or edit `.env.local` in the frontend folder:

```bash
# frontend/.env.local
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-ABC123XYZ
```

### 2.6 Verify Tracking

1. Deploy your changes
2. Go to Google Analytics
3. Click **"Reports"** → **"Realtime"**
4. Visit your website in another tab
5. You should see yourself as an active user

### 2.7 Set Up Conversions (Important!)

1. Go to **Admin** → **Events**
2. Mark these events as conversions:
   - `sign_up`
   - `payment_completed`
   - `project_generated`

---

## Step 3: Set Up Google Search Console

### 3.1 Add Your Property

1. Go to https://search.google.com/search-console
2. Click **"Add property"**
3. Select **"URL prefix"**
4. Enter: `https://bharatbuild.ai`
5. Click **"Continue"**

### 3.2 Verify Ownership

1. Choose **"HTML tag"** method
2. You'll see something like:
   ```html
   <meta name="google-site-verification" content="ABC123XYZ..." />
   ```
3. Copy ONLY the content value: `ABC123XYZ...`

### 3.3 Add to Your Project

Add to `.env.local`:

```bash
# frontend/.env.local
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-ABC123XYZ
NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION=ABC123XYZ...
```

### 3.4 Deploy and Verify

1. Deploy your changes
2. Go back to Search Console
3. Click **"Verify"**
4. Should show: **"Ownership verified"**

### 3.5 Submit Sitemap

1. In Search Console, click **"Sitemaps"** in left menu
2. Enter: `sitemap.xml`
3. Click **"Submit"**
4. Status should show: **"Success"**

### 3.6 Request Indexing

1. Click **"URL Inspection"** in left menu
2. Enter your homepage URL
3. Click **"Request Indexing"**
4. Repeat for important pages:
   - `https://bharatbuild.ai/pricing`
   - `https://bharatbuild.ai/register`
   - `https://bharatbuild.ai/showcase`
   - `https://bharatbuild.ai/blog`

---

## Step 4: Import Keywords to Google Ads

### 4.1 Access Google Ads

1. Go to https://ads.google.com
2. Sign in with your Google account
3. If new, follow setup wizard

### 4.2 Create a Campaign

1. Click **"+ New Campaign"**
2. Select goal: **"Website traffic"** or **"Leads"**
3. Select type: **"Search"**
4. Enter website: `bharatbuild.ai`
5. Name campaign: `BharatBuild - Search`
6. Click **"Continue"**

### 4.3 Import Keywords from CSV

1. Go to **Tools & Settings** (wrench icon) → **Keyword Planner**
2. Click **"Get search volume and forecasts"**
3. Click **"Upload file"**
4. Upload: `seo/google-ads-keyword-groups.csv`
5. Review keywords and create ad groups

### 4.4 Recommended Budget Allocation

| Campaign | Daily Budget | Priority |
|----------|--------------|----------|
| Student Projects | ₹500-1000 | HIGH |
| AI Code Generator | ₹300-500 | HIGH |
| Competitor Keywords | ₹200-400 | MEDIUM |
| Mobile Apps | ₹200-300 | MEDIUM |
| Startup MVP | ₹200-300 | MEDIUM |
| Campus Placement | ₹100-200 | LOW |

### 4.5 Set Up Conversion Tracking

1. Go to **Tools** → **Conversions**
2. Click **"+ New conversion action"**
3. Select **"Website"**
4. For each conversion:
   - Sign Up: Category = Sign-up, Value = ₹100
   - Payment: Category = Purchase, Value = Use actual value
   - Project Created: Category = Other, Value = ₹50

### 4.6 Link Google Analytics

1. Go to **Tools** → **Linked accounts**
2. Click **"Google Analytics (GA4)"**
3. Click **"Link"**
4. Select your GA4 property
5. Enable auto-tagging

---

## Step 5: Deploy and Submit Sitemap

### 5.1 Verify Sitemap Locally

```bash
# Start dev server
npm run dev

# Visit sitemap
open http://localhost:3000/sitemap.xml
```

You should see XML with all your pages listed.

### 5.2 Deploy to Production

```bash
# If using Vercel
vercel --prod

# If using other platforms, follow their deployment guide
```

### 5.3 Verify Production Sitemap

1. Visit: `https://bharatbuild.ai/sitemap.xml`
2. Verify all pages are listed
3. Check robots.txt: `https://bharatbuild.ai/robots.txt`

### 5.4 Submit to Search Engines

**Google:**
Already done in Step 3.5

**Bing:**
1. Go to https://www.bing.com/webmasters
2. Add your site
3. Submit sitemap

---

## Step 6: Blog is Ready!

### Blog Routes Created

| URL | Description |
|-----|-------------|
| `/blog` | Blog listing page |
| `/blog/[slug]` | Individual blog posts |

### Blog Posts Available

1. `/blog/complete-final-year-project-with-ai`
2. `/blog/ieee-format-project-report-guide`
3. `/blog/ai-code-generators-compared`
4. `/blog/build-mvp-without-coding`
5. `/blog/50-final-year-project-ideas-cse`

### Adding New Blog Posts

Edit `frontend/src/app/blog/[slug]/page.tsx` and add to the `blogPostsContent` object:

```typescript
'your-new-post-slug': {
  title: 'Your Post Title',
  excerpt: 'Short description...',
  content: `
## Your Content Here

Write in Markdown format...
  `,
  author: 'BharatBuild Team',
  date: '2024-12-20',
  readTime: '10 min read',
  category: 'Category',
  tags: ['tag1', 'tag2'],
  keywords: ['keyword1', 'keyword2'],
},
```

Also update `sitemap.ts` with the new post.

---

## Verification Checklist

After completing all steps, verify:

```
[ ] og-image.png exists in /public
[ ] twitter-image.png exists in /public
[ ] GA4 shows real-time visitors
[ ] Search Console shows "Ownership verified"
[ ] Sitemap submitted successfully
[ ] /blog page loads correctly
[ ] Individual blog posts load
[ ] OG images show in social sharing tests
```

### Test Tools

- **OG Images:** https://www.opengraph.xyz/
- **Twitter Cards:** https://cards-dev.twitter.com/validator
- **Structured Data:** https://search.google.com/test/rich-results
- **PageSpeed:** https://pagespeed.web.dev/

---

## Environment Variables Summary

Your complete `.env.local` should have:

```bash
# API
NEXT_PUBLIC_API_URL=https://api.bharatbuild.ai/api/v1
NEXT_PUBLIC_WS_URL=wss://api.bharatbuild.ai/ws

# Analytics & SEO
NEXT_PUBLIC_GA_MEASUREMENT_ID=G-XXXXXXXXXX
NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION=your-verification-code

# App
NEXT_PUBLIC_APP_NAME=BharatBuild AI
NEXT_PUBLIC_APP_DOMAIN=bharatbuild.ai
```

---

## Support

For questions: info@bharatbuild.ai

---

**All done!** Your SEO setup is complete. Monitor performance in:
- Google Analytics: https://analytics.google.com
- Google Search Console: https://search.google.com/search-console
- Google Ads: https://ads.google.com
