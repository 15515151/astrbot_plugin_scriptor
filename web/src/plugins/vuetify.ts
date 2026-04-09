import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { ScriptorDarkTheme, ScriptorLightTheme } from '@/theme'

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'scriptorDark',
    themes: {
      scriptorDark: ScriptorDarkTheme,
      scriptorLight: ScriptorLightTheme,
    },
  },
  defaults: {
    VCard: {
      rounded: 'lg',
      elevation: 2,
    },
    VBtn: {
      rounded: 'lg',
    },
    VTextField: {
      rounded: 'lg',
      variant: 'outlined',
    },
    VSelect: {
      rounded: 'lg',
      variant: 'outlined',
    },
    VTextarea: {
      rounded: 'lg',
      variant: 'outlined',
    },
    VTooltip: {
      location: 'top',
    },
    VChip: {
      rounded: 'lg',
    },
  },
})
