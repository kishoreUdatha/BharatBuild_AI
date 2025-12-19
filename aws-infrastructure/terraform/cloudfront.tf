# =============================================================================
# CloudFront Distribution for Global CDN
# Only created when domain_name is configured
# =============================================================================

# CloudFront Distribution (only when domain is configured)
resource "aws_cloudfront_distribution" "main" {
  count               = var.domain_name != "" ? 1 : 0
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "BharatBuild CDN"
  default_root_object = ""
  price_class         = "PriceClass_200"  # Use all edge locations except South America and Australia
  aliases             = [var.domain_name, "www.${var.domain_name}"]

  # Origin for ALB
  origin {
    domain_name = aws_lb.main.dns_name
    origin_id   = "ALB"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }

    custom_header {
      name  = "X-Custom-Header"
      value = "bharatbuild-cloudfront"
    }
  }

  # Origin for S3 (static assets)
  origin {
    domain_name = aws_s3_bucket.storage.bucket_regional_domain_name
    origin_id   = "S3-Static"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.main[0].cloudfront_access_identity_path
    }
  }

  # Default cache behavior (ALB)
  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "ALB"

    forwarded_values {
      query_string = true
      headers      = ["Host", "Origin", "Authorization", "Accept", "Accept-Language"]

      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
    compress               = true
  }

  # API cache behavior (no caching)
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "ALB"

    forwarded_values {
      query_string = true
      headers      = ["*"]

      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "https-only"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
  }

  # WebSocket behavior
  ordered_cache_behavior {
    path_pattern     = "/ws/*"
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "ALB"

    forwarded_values {
      query_string = true
      headers      = ["*"]

      cookies {
        forward = "all"
      }
    }

    viewer_protocol_policy = "https-only"
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0
  }

  # Static assets cache behavior
  ordered_cache_behavior {
    path_pattern     = "/static/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-Static"

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "https-only"
    min_ttl                = 86400      # 1 day
    default_ttl            = 604800     # 7 days
    max_ttl                = 2592000    # 30 days
    compress               = true
  }

  # Next.js static files
  ordered_cache_behavior {
    path_pattern     = "/_next/static/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "ALB"

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "https-only"
    min_ttl                = 86400
    default_ttl            = 604800
    max_ttl                = 31536000  # 1 year
    compress               = true
  }

  # SSL Certificate
  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.cloudfront[0].arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  tags = {
    Name = "${var.app_name}-cdn"
  }

  depends_on = [aws_acm_certificate_validation.cloudfront]
}

# Origin Access Identity for S3 (only when domain is configured)
resource "aws_cloudfront_origin_access_identity" "main" {
  count   = var.domain_name != "" ? 1 : 0
  comment = "OAI for BharatBuild S3 bucket"
}

# S3 bucket policy for CloudFront (only when domain is configured)
resource "aws_s3_bucket_policy" "storage_cloudfront" {
  count  = var.domain_name != "" ? 1 : 0
  bucket = aws_s3_bucket.storage.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "CloudFrontAccess"
        Effect    = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.main[0].iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.storage.arn}/*"
      }
    ]
  })
}

# CloudFront certificate (must be in us-east-1, only when domain is configured)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

resource "aws_acm_certificate" "cloudfront" {
  count                     = var.domain_name != "" ? 1 : 0
  provider                  = aws.us_east_1
  domain_name               = var.domain_name
  subject_alternative_names = ["*.${var.domain_name}"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "cloudfront" {
  count                   = var.domain_name != "" && var.route53_zone_exists ? 1 : 0
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.cloudfront[0].arn
  validation_record_fqdns = [for record in aws_route53_record.cloudfront_cert_validation : record.fqdn]
}

resource "aws_route53_record" "cloudfront_cert_validation" {
  for_each = var.domain_name != "" && var.route53_zone_exists ? {
    for dvo in aws_acm_certificate.cloudfront[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main[0].zone_id
}

# Update Route53 to point to CloudFront (only when domain is configured AND zone exists)
resource "aws_route53_record" "cloudfront" {
  count   = var.domain_name != "" && var.route53_zone_exists ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.main[0].domain_name
    zone_id                = aws_cloudfront_distribution.main[0].hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "cloudfront_www" {
  count   = var.domain_name != "" && var.route53_zone_exists ? 1 : 0
  zone_id = data.aws_route53_zone.main[0].zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.main[0].domain_name
    zone_id                = aws_cloudfront_distribution.main[0].hosted_zone_id
    evaluate_target_health = false
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (only available when domain is configured)"
  value       = var.domain_name != "" ? aws_cloudfront_distribution.main[0].domain_name : "N/A - No domain configured"
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (only available when domain is configured)"
  value       = var.domain_name != "" ? aws_cloudfront_distribution.main[0].id : "N/A - No domain configured"
}
