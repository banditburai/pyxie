---
title: "Pyxie Components Guide"
date: 2024-03-19
author: "Pyxie Team"
slug: "components-guide"
category: "Design"
summary: "Learn how to create and organize interactive components in Pyxie"
reading_time: "5 min read"
---

<featured_image>
![Component Examples](pyxie:daisy/1200/600)
</featured_image>

<toc>
- [UI Components](#ui-components)
- [Interactive Elements](#interactive-elements)
- [Data Input Components](#data-input-components)
</toc>

<content>
# Pyxie Components Guide

Learn how to create and organize interactive components using FastHTML in Pyxie.

## UI Components

Here are some examples of reusable UI components you can add to your markdown:

### Alert Messages

Alerts help draw attention to important information. They come in different styles and can include icons for better visual hierarchy:

<fasthtml>
def iconify(icon, cls=None, **kwargs):
    return ft_hx('iconify-icon', icon=icon, cls=cls, **kwargs)

def AlertExamples():
    return Div(
        Div(
            iconify("lucide:info", cls="text-lg"),
            Span("This is an informational message."),
            role="alert",
            cls="alert alert-info mb-2"
        ),
        Div(
            iconify("lucide:check-circle", cls="text-lg"),
            Span("Your action was completed successfully."),
            role="alert",
            cls="alert alert-success"
        ),
        cls="mb-8"
    )

show(AlertExamples())
</fasthtml>

The alerts above use DaisyUI's `alert` component combined with Lucide icons. You can customize their appearance using different color schemes like `alert-info`, `alert-success`, `alert-warning`, or `alert-error`.

### Call to Action

Call to action components help guide users towards important actions. They work best when placed strategically within your content:

<fasthtml>
def CallToAction():
    return Div(
        H3("Ready to get started?", cls="text-2xl font-bold mb-4"),
        P("Join our community and start building amazing content.", cls="mb-4"),
        Button(
            "Get Started",
            cls="btn btn-primary"
        ),
        cls="text-center p-8 bg-base-200 rounded-lg"
    )

show(CallToAction())
</fasthtml>

Notice how the call to action uses a contrasting background (`bg-base-200`) to stand out from the regular content. This is just one way to style these components - you can adjust the colors, padding, and border radius to match your design.

## Interactive Elements

While static content is great for documentation, interactive elements can make your content more engaging and help users better understand complex topics.

### Expandable Section

Expandable sections are perfect for progressive disclosure - showing additional details only when users need them:

<fasthtml>
def iconify(icon, cls=None, **kwargs):
    return ft_hx('iconify-icon', icon=icon, cls=cls, **kwargs)

def Expandable():
    return Div(
        Div(
            Input(type="checkbox"),
            Div(
                iconify("lucide:chevron-down", cls="text-2xl transition-transform [:checked+div>iconify-icon]:-rotate-180"),
                Span("Click to learn more"),                
                cls="collapse-title text-xl font-medium flex items-center gap-2"
            ),
            Div(
                P("This content can be shown or hidden on demand, making your document more interactive and engaging."),
                cls="collapse-content"
            ),
            cls="collapse bg-base-200"
        ),
        cls="mb-8"
    )

show(Expandable())
</fasthtml>

The expandable section above uses DaisyUI's `collapse` component with a smooth animation. It's great for:
- Hiding lengthy explanations
- Organizing FAQs
- Showing code examples
- Revealing additional details

### DaisyUI Button Variants

Buttons are fundamental to any interface. DaisyUI provides several button styles that you can mix and match:

<fasthtml>
def ButtonExamples():
    return Div(
        H3("Button Variants", cls="text-xl font-bold mb-4"),
        Div(
            Button("Default", cls="btn"),
            Button("Primary", cls="btn btn-primary"),
            Button("Secondary", cls="btn btn-secondary"),
            Button("Accent", cls="btn btn-accent"),
            Button("Ghost", cls="btn btn-ghost"),
            Button("Link", cls="btn btn-link"),
            cls="flex flex-wrap gap-2 mb-4"
        ),       
        cls="mb-8"
    )

show(ButtonExamples())
</fasthtml>

Each button variant serves a different purpose:
- `btn-primary` for main actions
- `btn-secondary` for alternative actions
- `btn-accent` for special emphasis
- `btn-ghost` for subtle actions
- `btn-link` for navigation-style buttons

## Data Input Components

Forms are essential for collecting user input.

### Contact Form Example

Here's a basic contact form that demonstrates proper form structure and styling:

<fasthtml>
def FormExample():
    return Div(
        H3("Form Components", cls="text-xl font-bold mb-4"),
        P("Pyxie provides several form components for data input:", cls="mb-4"),
        Fieldset(
            Legend("Contact Form", cls="fieldset-legend"),
            Label("Email", cls="fieldset-label"),
            Input(type="email", placeholder="Enter your email", cls="w-full input"),
            Label("Message", cls="fieldset-label"),
            Textarea(placeholder="Your message", cls="w-full textarea textarea-bordered h-24"),
            Button("Submit", type="submit", cls="btn btn-primary mt-4"),
            cls="fieldset w-full bg-base-200 border border-base-300 p-4 rounded-box"
        ),
        cls="mb-8"
    )

show(FormExample())
</fasthtml>

The form above uses `Fieldset` to group related inputs, which helps with:
- Semantic HTML structure
- Improved accessibility
- Visual organization
- Logical grouping of form elements

### Login Form Example

For a more focused data entry experience, you might want a compact form like this login example:

<fasthtml>
def LoginForm():
    return Div(
        H3("Login Form", cls="text-xl font-bold mb-4"),
        Fieldset(
            Legend("Login", cls="fieldset-legend"),
            Label("Email", cls="fieldset-label"),
            Input(type="email", placeholder="Email", cls="input"),
            Label("Password", cls="fieldset-label"),
            Input(type="password", placeholder="Password", cls="input"),
            Button("Login", cls="btn btn-neutral mt-4"),
            cls="fieldset w-xs bg-base-200 border border-base-300 p-4 rounded-box"
        ),
        cls="mb-8"
    )

show(LoginForm())
</fasthtml>

This login form demonstrates several best practices:
- Clear visual hierarchy with proper spacing
- Appropriate input types for different data
- Consistent styling with the rest of the UI
- Compact layout for focused tasks

Remember that all these components can be customized further using DaisyUI's utility classes and color schemes. You can adjust sizes, colors, spacing, and more to match your site's design language.

</content>

<conclusion>
Components can greatly enhance your markdown content, making it more engaging and interactive. Use them thoughtfully to create better user experiences while maintaining good performance and accessibility.
</conclusion>

<share>
<div class="flex gap-3">
  <a href="https://twitter.com/share?text=Pyxie Components Guide&url=https://example.com/post/components-guide" target="_blank" class="btn btn-sm btn-outline">
    <iconify-icon icon="fa:twitter" class="mr-2"></iconify-icon> Share on Twitter
  </a>
  <a href="https://www.facebook.com/sharer/sharer.php?u=https://example.com/post/components-guide" target="_blank" class="btn btn-sm btn-outline">
    <iconify-icon icon="fa:facebook" class="mr-2"></iconify-icon> Share on Facebook
  </a>
</div>
</share> 