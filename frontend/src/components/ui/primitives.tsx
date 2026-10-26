/* Primitives on Radix (shadcn/ui pattern), in Coral's material: letterpress cards for controls,
   an ink board for the one primary action, cotton stock for anything that floats. */
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as SelectPrimitive from "@radix-ui/react-select";
import { Check, ChevronDown, X } from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Button: pressed cards, 36px tall with a 44px hit target ── */
export const buttonVariants = cva(
  "hit inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-stock text-[14px] font-medium select-none cursor-pointer transition-transform duration-200 ease-out hover:-translate-y-px active:translate-y-px disabled:opacity-55 disabled:hover:translate-y-0 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-board text-board-type shadow-[var(--cast-stock)] hover:shadow-[var(--cast-stock-lift)]",
        card: "stock hover:shadow-[var(--edge-stock),var(--cast-stock-lift)]",
        ghost: "text-ink hover:bg-paper-2 hover:translate-y-0 active:translate-y-0",
        destructive: "text-bad hover:bg-paper-2 hover:translate-y-0 active:translate-y-0",
      },
      size: { default: "h-9 px-4", sm: "h-8 px-3 text-[13px]", icon: "size-9" },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export function Button({ className, variant, size, asChild, type, ...props }:
  React.ComponentProps<"button"> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "button";
  return <Comp {...(asChild ? {} : { type: type ?? "button" })} className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}

/* ── Status chip: an ink outline. Coral is kept for the pressed "Live" stamp. ── */
const badgeVariants = cva("inline-flex items-center rounded-input border px-2 py-px text-[12.5px] font-medium whitespace-nowrap", {
  variants: {
    variant: {
      default: "border-rule-2 text-muted",
      strong: "border-ink text-ink",
      bad: "border-bad text-bad",
    },
  },
  defaultVariants: { variant: "default" },
});
export function Badge({ className, variant, ...props }: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

/* ── Inputs: constant 1px edge, focus is the outline ── */
const field = "rounded-input border border-muted bg-cotton text-print outline-none focus-visible:outline-2 focus-visible:outline-offset-[-1px] focus-visible:outline-focus disabled:opacity-55";
export function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return <textarea className={cn(field, "w-full min-h-28 px-3.5 py-3 text-[16px] leading-relaxed resize-y scrollbar-thin", className)} {...props} />;
}
export function Input({ className, ...props }: React.ComponentProps<"input">) {
  return <input className={cn(field, "h-9 px-3 text-[14px]", className)} {...props} />;
}

/* ── Tabs: underline ── */
export const Tabs = TabsPrimitive.Root;
export function TabsList({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.List>) {
  return <TabsPrimitive.List className={cn("flex items-center gap-6 border-b border-rule", className)} {...props} />;
}
export function TabsTrigger({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  return <TabsPrimitive.Trigger className={cn("-mb-px inline-flex h-10 items-center gap-1.5 border-b-2 border-transparent text-[14px] font-medium text-muted data-[state=active]:border-ink data-[state=active]:text-ink cursor-pointer whitespace-nowrap", className)} {...props} />;
}
export const TabsContent = TabsPrimitive.Content;

/* ── Tooltip: waits on hover, instant on focus ── */
export const TooltipProvider = TooltipPrimitive.Provider;
export function Tooltip({ content, children }: { content: React.ReactNode; children: React.ReactNode }) {
  return (
    <TooltipPrimitive.Root delayDuration={800}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content sideOffset={6} className="z-[600] rounded-input bg-board px-2.5 py-1 text-[12.5px] text-board-type">
          {content}
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}

/* ── Dialog: one sheet of stock on the desk ── */
export const Dialog = DialogPrimitive.Root;
export function DialogContent({ className, children, title, ...props }: React.ComponentProps<typeof DialogPrimitive.Content> & { title: string }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-[400] bg-board/40" />
      <DialogPrimitive.Content className={cn("stock fixed left-1/2 top-[10%] z-[400] w-[calc(100%-32px)] max-w-xl -translate-x-1/2 rounded-card outline-none", className)} {...props}>
        <DialogPrimitive.Title className="sr-only">{title}</DialogPrimitive.Title>
        {children}
        <DialogPrimitive.Close className="absolute right-3 top-3 grid size-9 place-items-center rounded-input text-muted hover:bg-paper-2 hover:text-ink cursor-pointer" aria-label="Close"><X className="size-4" /></DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

/* ── Select ── */
export function Select({ value, onValueChange, options, className, ariaLabel }: {
  value: string; onValueChange: (v: string) => void; options: { value: string; label: string }[]; className?: string; ariaLabel: string;
}) {
  return (
    <SelectPrimitive.Root value={value} onValueChange={onValueChange}>
      <SelectPrimitive.Trigger aria-label={ariaLabel} className={cn(field, "inline-flex h-9 items-center justify-between gap-2 px-3 text-[14px] cursor-pointer", className)}>
        <SelectPrimitive.Value />
        <SelectPrimitive.Icon><ChevronDown className="size-4 text-muted" /></SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content position="popper" sideOffset={4} className="stock z-[600] min-w-[var(--radix-select-trigger-width)] rounded-card p-1">
          <SelectPrimitive.Viewport>
            {options.map((o) => (
              <SelectPrimitive.Item key={o.value} value={o.value} className="relative flex cursor-pointer select-none items-center rounded-input py-2 pl-8 pr-3 text-[14px] outline-none data-[highlighted]:bg-paper-2">
                <SelectPrimitive.ItemIndicator className="absolute left-2.5"><Check className="size-4" /></SelectPrimitive.ItemIndicator>
                <SelectPrimitive.ItemText>{o.label}</SelectPrimitive.ItemText>
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  );
}

/* ── Meter: a ruled bar ── */
export function Meter({ value, max = 10, className, weak }: { value: number; max?: number; className?: string; weak?: boolean }) {
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-[2px] bg-rule", className)} role="meter" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max}>
      <div className={cn("h-full origin-left", weak ? "bg-muted" : "bg-ink")} style={{ transform: `scaleX(${Math.max(0, Math.min(1, value / max))})` }} />
    </div>
  );
}

/* ── Groove: a choice of two to four, a cotton card riding to the chosen stop ── */
export function Groove<T extends string>({ value, onChange, options, label }: {
  value: T; onChange: (v: T) => void; options: { value: T; label: React.ReactNode; aria?: string }[]; label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="groove inline-flex items-center gap-1 p-1">
      {options.map((o) => (
        <button key={o.value} type="button" role="radio" aria-checked={value === o.value} aria-label={o.aria} onClick={() => onChange(o.value)}
          className={cn("flex h-8 items-center gap-2 rounded-input px-3 text-[13.5px] font-medium cursor-pointer whitespace-nowrap",
            value === o.value ? "stock text-print" : "text-muted hover:text-ink")}>
          {o.label}
        </button>
      ))}
    </div>
  );
}
