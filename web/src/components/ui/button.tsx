import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-lg border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-all outline-none select-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 active:not-aria-[haspopup]:translate-y-px disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/80",
        outline:
          "border-border bg-background hover:bg-muted hover:text-foreground aria-expanded:bg-muted aria-expanded:text-foreground dark:border-input dark:bg-input/30 dark:hover:bg-input/50",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-[color-mix(in_oklch,var(--secondary),var(--foreground)_5%)] aria-expanded:bg-secondary aria-expanded:text-secondary-foreground",
        ghost:
          "hover:bg-muted hover:text-foreground aria-expanded:bg-muted aria-expanded:text-foreground dark:hover:bg-muted/50",
        destructive:
          "bg-destructive/10 text-destructive hover:bg-destructive/20 focus-visible:border-destructive/40 focus-visible:ring-destructive/20 dark:bg-destructive/20 dark:hover:bg-destructive/30 dark:focus-visible:ring-destructive/40",
        link: "text-primary underline-offset-4 hover:underline",
      },
      // ---------------------------------------------------------------------
      //  DENSIDAD. Se decide AQUI, una vez, y no pantalla por pantalla: hacerlo
      //  por pantalla significa que la numero treinta y uno se olvida y que
      //  cada dialogo nuevo reabre el debate.
      //
      //  LA FORMA DE LA CLASE ES `valor-escritorio max-sm:valor-movil`, NUNCA
      //  al reves. `tailwind-merge` no ve conflicto entre `h-12` y `sm:h-8`
      //  —son modificadores distintos— pero si entre `h-12` y `h-8`. Con la
      //  forma ascendente, un `className="h-12"` de quien llama dejaria
      //  `h-12 sm:h-8` y el boton ENCOGERIA a 32 px en escritorio, sin que
      //  nadie lo note. Lo ancla `button.spec.ts`.
      //
      //  Y el escalon es `sm` (640 px), uno solo: un iPad mini en vertical mide
      //  744 px, asi que anclar en `md` reflujaria una tableta que hoy esta
      //  bien.
      // ---------------------------------------------------------------------
      size: {
        default:
          "h-8 max-sm:h-11 gap-1.5 px-2.5 max-sm:px-3 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        xs: "h-6 gap-1 rounded-[min(var(--radius-md),10px)] px-2 text-xs in-data-[slot=button-group]:rounded-lg has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-7 max-sm:h-10 gap-1 rounded-[min(var(--radius-md),12px)] px-2.5 max-sm:px-3 text-[0.8rem] max-sm:text-sm in-data-[slot=button-group]:rounded-lg has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-9 max-sm:h-11 gap-1.5 px-2.5 max-sm:px-4 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        /**
         * 44 px exactos. Es el UNICO tamano junto a `key` sin `max-sm:`: mide lo
         * mismo a cualquier ancho porque marca lo que se pulsa de pie, con las
         * manos ocupadas, en el salon o delante del tablero de cocina.
         */
        touch: "h-11 gap-2 px-4 text-base",
        /**
         * 56 px. Las teclas del PIN, los mas y menos de cantidad, «Cobrar» y
         * «Enviar a cocina»: lo que se pulsa casi sin mirar.
         */
        key: "h-14 gap-2 px-5 text-lg font-semibold",
        icon: "size-8 max-sm:size-11",
        "icon-xs":
          "size-6 rounded-[min(var(--radius-md),10px)] in-data-[slot=button-group]:rounded-lg [&_svg:not([class*='size-'])]:size-3",
        "icon-sm":
          "size-7 max-sm:size-10 rounded-[min(var(--radius-md),12px)] in-data-[slot=button-group]:rounded-lg",
        "icon-lg": "size-9 max-sm:size-11",
        "icon-touch": "size-11 [&_svg:not([class*='size-'])]:size-5",
        "icon-key": "size-14 [&_svg:not([class*='size-'])]:size-6",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
