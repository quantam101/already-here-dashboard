// Platform-specific share URL builders.
// Returns null when the platform has no web composer (operator must paste manually).

const truncate = (s, n) => (s || "").slice(0, n);

export const PLATFORM_LABELS = {
  reddit: "Reddit",
  linkedin: "LinkedIn",
  twitter: "X / Twitter",
  x: "X / Twitter",
  facebook: "Facebook",
  tiktok: "TikTok",
  youtube: "YouTube",
  youtube_shorts: "YouTube",
  instagram: "Instagram",
  medium: "Medium",
  blog: "Blog",
};

export function platformShareUrl(platform, { title = "", body = "", url = "" } = {}) {
  const p = (platform || "").toLowerCase();
  const t = encodeURIComponent(title);
  const b = encodeURIComponent(body);
  const u = encodeURIComponent(url);
  switch (p) {
    case "reddit":
      // text post composer — title + selftext pre-filled
      return `https://www.reddit.com/submit?title=${t}&text=${encodeURIComponent(truncate(body, 10000))}`;
    case "linkedin":
      // LinkedIn share composer (supports URL or text-only)
      return url
        ? `https://www.linkedin.com/sharing/share-offsite/?url=${u}`
        : `https://www.linkedin.com/feed/?shareActive=true&text=${encodeURIComponent(truncate(`${title}\n\n${body}`, 3000))}`;
    case "twitter":
    case "x":
      return `https://twitter.com/intent/tweet?text=${encodeURIComponent(truncate(`${title} ${body}`, 280))}`;
    case "facebook":
      return url
        ? `https://www.facebook.com/sharer/sharer.php?u=${u}&quote=${t}`
        : null;
    case "medium":
      return "https://medium.com/new-story";
    case "tiktok":
      return "https://www.tiktok.com/upload";
    case "youtube":
    case "youtube_shorts":
      return "https://studio.youtube.com/channel/upload";
    case "instagram":
      // No web composer
      return null;
    case "blog":
      return null;
    default:
      return null;
  }
}

export function platformLabel(platform) {
  return PLATFORM_LABELS[(platform || "").toLowerCase()] || platform;
}
