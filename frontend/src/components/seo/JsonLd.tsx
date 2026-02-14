'use client'

// Organization Schema
export function OrganizationJsonLd() {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'BharatBuild AI',
    url: 'https://bharatbuild.ai',
    logo: 'https://bharatbuild.ai/logo.png',
    description: "India's leading AI-powered code generation platform for students, developers, and startups.",
    foundingDate: '2024',
    founders: [
      {
        '@type': 'Person',
        name: 'BharatBuild Team',
      },
    ],
    address: {
      '@type': 'PostalAddress',
      addressLocality: 'Hyderabad',
      addressCountry: 'IN',
    },
    contactPoint: {
      '@type': 'ContactPoint',
      telephone: '+91-98765-43210',
      contactType: 'customer service',
      email: 'info@bharatbuild.ai',
    },
    sameAs: [
      'https://twitter.com/bharatbuild',
      'https://linkedin.com/company/bharatbuild',
      'https://github.com/bharatbuild',
      'https://youtube.com/@bharatbuild',
    ],
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

// Software Application Schema
export function SoftwareApplicationJsonLd() {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: 'BharatBuild AI',
    applicationCategory: 'DeveloperApplication',
    operatingSystem: 'Web',
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'INR',
      description: 'Free tier with 3 projects',
    },
    aggregateRating: {
      '@type': 'AggregateRating',
      ratingValue: '4.8',
      ratingCount: '10000',
      bestRating: '5',
      worstRating: '1',
    },
    featureList: [
      'AI Code Generation',
      'Live Preview',
      'Auto Error Fixing',
      'Project Documentation',
      'Mobile App Generation',
      'Multiple Framework Support',
    ],
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

// FAQ Schema
export function FAQJsonLd() {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: [
      {
        '@type': 'Question',
        name: 'What is BharatBuild AI?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: "BharatBuild AI is India's leading AI-powered code generation platform that helps students, developers, and startups build complete applications with source code, documentation, and deployment capabilities using 31+ specialized AI agents.",
        },
      },
      {
        '@type': 'Question',
        name: 'How does BharatBuild generate code?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'BharatBuild uses 31+ specialized AI agents including Planner, Architect, Coder, Tester, and Debugger agents that work together to understand your requirements and generate production-ready code in real-time.',
        },
      },
      {
        '@type': 'Question',
        name: 'Is BharatBuild free to use?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'Yes! BharatBuild offers a free tier with 3 complete projects. You can generate full source code, documentation, and presentations without paying anything. Upgrade to Pro for unlimited projects.',
        },
      },
      {
        '@type': 'Question',
        name: 'What programming languages does BharatBuild support?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'BharatBuild supports 50+ technologies including React, Next.js, Vue, Angular, Node.js, Python, Django, FastAPI, Flutter, React Native, PostgreSQL, MongoDB, and many more.',
        },
      },
      {
        '@type': 'Question',
        name: 'Can BharatBuild generate my final year project?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'Yes! BharatBuild specializes in generating complete final year projects with source code, 60-80 page IEEE format project reports, PPT presentations, SRS documents, and 50+ viva questions with answers.',
        },
      },
      {
        '@type': 'Question',
        name: 'How is BharatBuild different from ChatGPT or GitHub Copilot?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'Unlike ChatGPT or Copilot which assist with code snippets, BharatBuild generates complete, production-ready applications with proper architecture, error handling, documentation, and deployment configurations using specialized AI agents for each task.',
        },
      },
    ],
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

// Product Schema for Pricing
export function ProductJsonLd() {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: 'BharatBuild AI Pro',
    description: 'Unlimited AI-powered code generation with all features',
    brand: {
      '@type': 'Brand',
      name: 'BharatBuild AI',
    },
    offers: {
      '@type': 'AggregateOffer',
      lowPrice: '0',
      highPrice: '4499',
      priceCurrency: 'INR',
      offerCount: '3',
      offers: [
        {
          '@type': 'Offer',
          name: 'Free Plan',
          price: '0',
          priceCurrency: 'INR',
          description: '3 free projects with basic features',
        },
        {
          '@type': 'Offer',
          name: 'Pro Plan',
          price: '999',
          priceCurrency: 'INR',
          description: 'Unlimited projects with all features',
        },
        {
          '@type': 'Offer',
          name: 'Premium Plan',
          price: '4499',
          priceCurrency: 'INR',
          description: 'Lifetime access with priority support',
        },
      ],
    },
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

// Breadcrumb Schema
export function BreadcrumbJsonLd({ items }: { items: { name: string; url: string }[] }) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: item.url,
    })),
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

// WebSite Schema with SearchAction
export function WebsiteJsonLd() {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: 'BharatBuild AI',
    url: 'https://bharatbuild.ai',
    description: "India's #1 AI Code & Project Generator",
    potentialAction: {
      '@type': 'SearchAction',
      target: {
        '@type': 'EntryPoint',
        urlTemplate: 'https://bharatbuild.ai/showcase?q={search_term_string}',
      },
      'query-input': 'required name=search_term_string',
    },
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}

// Article Schema for Blog Posts
export function ArticleJsonLd({
  title,
  description,
  url,
  datePublished,
  dateModified,
  authorName = 'BharatBuild AI',
  image = 'https://bharatbuild.ai/og-image.png',
}: {
  title: string
  description: string
  url: string
  datePublished: string
  dateModified?: string
  authorName?: string
  image?: string
}) {
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: title,
    description: description,
    url: url,
    datePublished: datePublished,
    dateModified: dateModified || datePublished,
    author: {
      '@type': 'Organization',
      name: authorName,
      url: 'https://bharatbuild.ai',
    },
    publisher: {
      '@type': 'Organization',
      name: 'BharatBuild AI',
      logo: {
        '@type': 'ImageObject',
        url: 'https://bharatbuild.ai/logo.png',
      },
    },
    image: {
      '@type': 'ImageObject',
      url: image,
    },
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': url,
    },
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
    />
  )
}
