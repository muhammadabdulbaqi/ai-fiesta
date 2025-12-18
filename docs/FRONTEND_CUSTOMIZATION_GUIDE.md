# Frontend Customization Guide

This guide explains how to customize the AI Fiesta frontend, including changing the logo, colors, branding, and other UI elements.

## Table of Contents

1. [Changing the Logo](#changing-the-logo)
2. [Customizing Colors and Themes](#customizing-colors-and-themes)
3. [Modifying Branding Text](#modifying-branding-text)
4. [Customizing Icons](#customizing-icons)
5. [Layout Customization](#layout-customization)
6. [Advanced Customization](#advanced-customization)

## Changing the Logo

### Method 1: Replace Logo Image

1. **Locate the logo file:**
   - The logo is displayed in `frontend/components/sidebar.tsx`
   - Currently uses an emoji (🎉) as a placeholder

2. **Add your logo image:**
   ```bash
   # Place your logo in the public folder
   frontend/public/logo.png  # or logo.svg, logo.jpg
   ```

3. **Update the sidebar component:**
   
   Open `frontend/components/sidebar.tsx` and find:
   ```tsx
   <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
     <span className="text-white font-bold text-lg">🎉</span>
   </div>
   ```
   
   Replace with:
   ```tsx
   <div className="w-8 h-8 rounded-lg flex items-center justify-center">
     <img 
       src="/logo.png" 
       alt="AI Fiesta" 
       className="w-full h-full object-contain"
     />
   </div>
   ```

### Method 2: Update Header Logo

The header logo is in `frontend/app/page.tsx`:

```tsx
<h1 className="font-semibold flex items-center gap-2 text-lg">
  <Sparkles className="w-5 h-5 text-primary" />
  AI Fiesta
</h1>
```

Replace with:
```tsx
<h1 className="font-semibold flex items-center gap-2 text-lg">
  <img src="/logo.png" alt="Logo" className="w-5 h-5" />
  Your Brand Name
</h1>
```

## Customizing Colors and Themes

### Theme Configuration

The app uses Tailwind CSS with CSS variables for theming. Colors are defined in `frontend/app/globals.css`.

### Primary Colors

Edit `frontend/app/globals.css` to change primary colors:

```css
:root {
  --primary: 222.2 47.4% 11.2%;        /* Primary color */
  --primary-foreground: 210 40% 98%;  /* Text on primary */
  --accent: 210 40% 96.1%;            /* Accent color */
  --accent-foreground: 222.2 47.4% 11.2%;
  /* ... other colors ... */
}
```

### Dark Mode Colors

Dark mode colors are also in `globals.css`:

```css
.dark {
  --primary: 210 40% 98%;
  --primary-foreground: 222.2 47.4% 11.2%;
  /* ... other dark mode colors ... */
}
```

### Quick Color Changes

1. **Primary Color (Buttons, Links):**
   - Find `--primary` in `globals.css`
   - Change HSL values to your brand color

2. **Background Colors:**
   - `--background`: Main background
   - `--card`: Card backgrounds
   - `--muted`: Muted backgrounds

3. **Text Colors:**
   - `--foreground`: Main text
   - `--muted-foreground`: Secondary text

## Modifying Branding Text

### App Name

1. **Sidebar:** `frontend/components/sidebar.tsx`
   ```tsx
   <span className="font-bold text-lg">AI Fiesta</span>
   ```

2. **Header:** `frontend/app/page.tsx`
   ```tsx
   <h1 className="font-semibold flex items-center gap-2 text-lg">
     <Sparkles className="w-5 h-5 text-primary" />
     AI Fiesta
   </h1>
   ```

3. **Page Title:** `frontend/app/layout.tsx`
   ```tsx
   export const metadata: Metadata = {
     title: "AI Fiesta",
     description: "Multi-model AI chat with token and credit tracking",
   }
   ```

### Footer Text

In `frontend/components/sidebar.tsx`:
```tsx
<div className="text-xs text-center text-muted-foreground">
  v0.1.0-beta
</div>
```

### Placeholder Text

In `frontend/app/page.tsx`:
```tsx
placeholder={
  mode === "multi-chat" 
    ? (selectedModels.length === 0 ? "Select at least one model..." : `Ask ${selectedModels.length} models...`)
    : (selectedModel ? `Ask ${selectedModel}...` : "Select a model...")
}
```

## Customizing Icons

### Provider Icons

Provider icons are located in `frontend/public/icons/`:

- `openai.png` - OpenAI logo
- `anthropic-1.svg` - Anthropic logo
- `Google_Gemini_icon_2025.svg.png` - Gemini logo
- `Grok-icon.svg.png` - Grok logo
- `perplexity-e6a4e1t06hd6dhczot580o.webp` - Perplexity logo

**To replace:**
1. Add your custom icon to `frontend/public/icons/`
2. Update the icon path in `frontend/components/multi-chat-model-selectors.tsx`:
   ```tsx
   const getProviderIcon = (provider: string) => {
     switch (provider.toLowerCase()) {
       case "openai":
         return "/icons/your-openai-icon.png"
       // ... other providers
     }
   }
   ```

### UI Icons

The app uses Lucide React icons. To change icons:

1. **Import different icons:**
   ```tsx
   import { YourIcon } from "lucide-react"
   ```

2. **Replace in components:**
   ```tsx
   <YourIcon className="w-4 h-4" />
   ```

## Layout Customization

### Sidebar Width

In `frontend/components/sidebar.tsx`:
```tsx
<div className="w-64 h-screen ...">  {/* Change w-64 to w-72, w-80, etc. */}
```

### Header Height

In `frontend/app/page.tsx`:
```tsx
<div className="border-b border-border bg-card/50 backdrop-blur-sm p-4 z-10 shrink-0">
  {/* Adjust p-4 to p-6 for more padding, or p-2 for less */}
</div>
```

### Model Selector Layout

In `frontend/components/multi-chat-model-selectors.tsx`:
```tsx
<div className="flex items-center gap-4 overflow-x-auto pb-2">
  {/* Adjust gap-4 to change spacing between model cards */}
</div>
```

### Response Column Width

In `frontend/components/model-response-column.tsx`:
```tsx
<div className={cn(
  "flex flex-col h-full min-w-[300px] max-w-[400px]",
  // Change min-w and max-w to adjust column width
)}>
```

## Advanced Customization

### Custom Fonts

1. **Add font files to `frontend/public/fonts/`**

2. **Update `frontend/app/layout.tsx`:**
   ```tsx
   import localFont from "next/font/local"
   
   const customFont = localFont({
     src: "../public/fonts/YourFont.woff2",
     variable: "--font-custom",
   })
   
   <body className={`${customFont.variable} font-sans antialiased`}>
   ```

3. **Update `tailwind.config.js`:**
   ```js
   theme: {
     extend: {
       fontFamily: {
         sans: ["var(--font-custom)", "sans-serif"],
       },
     },
   }
   ```

### Custom Animations

Add to `frontend/app/globals.css`:
```css
@keyframes your-animation {
  0% { /* ... */ }
  100% { /* ... */ }
}

.your-animation {
  animation: your-animation 1s ease-in-out;
}
```

### Custom Components

Create new components in `frontend/components/`:

```tsx
// frontend/components/custom-header.tsx
export function CustomHeader() {
  return (
    <div className="custom-header">
      {/* Your custom header */}
    </div>
  )
}
```

Then import and use:
```tsx
import { CustomHeader } from "@/components/custom-header"
```

### Environment-Specific Branding

Use environment variables for different branding:

1. **Add to `.env.local`:**
   ```
   NEXT_PUBLIC_APP_NAME=Your App Name
   NEXT_PUBLIC_LOGO_PATH=/logo.png
   ```

2. **Use in components:**
   ```tsx
   const appName = process.env.NEXT_PUBLIC_APP_NAME || "AI Fiesta"
   const logoPath = process.env.NEXT_PUBLIC_LOGO_PATH || "/logo.png"
   ```

## File Structure Reference

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout, metadata
│   ├── page.tsx            # Main chat page
│   └── globals.css         # Global styles, theme colors
├── components/
│   ├── sidebar.tsx         # Sidebar with logo and navigation
│   ├── chat-message.tsx    # Message display component
│   ├── multi-chat-model-selectors.tsx  # Model selector
│   └── model-response-column.tsx      # Response column
├── public/
│   ├── icons/              # Provider icons
│   └── logo.png            # Your logo (add here)
└── lib/
    └── api.ts              # API client
```

## Quick Customization Checklist

- [ ] Replace logo image in `public/logo.png`
- [ ] Update app name in `sidebar.tsx` and `page.tsx`
- [ ] Change primary colors in `globals.css`
- [ ] Update page title in `layout.tsx`
- [ ] Replace provider icons in `public/icons/`
- [ ] Customize placeholder text in `page.tsx`
- [ ] Adjust layout widths/spacing as needed
- [ ] Update footer version text

## Tips

1. **Test in both light and dark modes** - Ensure colors work in both themes
2. **Keep logo aspect ratio** - Maintain proper logo proportions
3. **Use SVG for logos** - Better scalability and smaller file size
4. **Optimize images** - Compress images before adding to `public/`
5. **Maintain accessibility** - Ensure sufficient color contrast
6. **Test responsive design** - Check mobile and tablet views

## Support

For advanced customization needs or questions:
- Check the Next.js documentation: https://nextjs.org/docs
- Review Tailwind CSS docs: https://tailwindcss.com/docs
- Consult the codebase comments for component-specific details

