from .models import Reminder, MenstrualUserSetting


THEME_PALETTES = {
    MenstrualUserSetting.THEME_DEFAULT: {
        'primary': '#2F6B3F',
        'secondary': '#7FB77E',
        'accent': '#F7C85C',
        'on_color': '#102617',
    },
    MenstrualUserSetting.THEME_GOLD: {
        'primary': '#D4AF37',
        'secondary': '#FFD700',
        'accent': '#FFB300',
        'on_color': '#2b1e00',
    },
    MenstrualUserSetting.THEME_ROSE: {
        'primary': '#B23A6A',
        'secondary': '#E07AA5',
        'accent': '#FFB6D0',
        'on_color': '#2a1020',
    },
    MenstrualUserSetting.THEME_OCEAN: {
        'primary': '#1F6FAE',
        'secondary': '#66B7D8',
        'accent': '#7DD3FC',
        'on_color': '#082032',
    },
    MenstrualUserSetting.THEME_LAVENDER: {
        'primary': '#6D4EA1',
        'secondary': '#A88BD8',
        'accent': '#CBB7F5',
        'on_color': '#1f1336',
    },
}

def reminders_processor(request):
    theme_key = MenstrualUserSetting.THEME_DEFAULT
    selected_palette = THEME_PALETTES[theme_key].copy()

    if request.user.is_authenticated:
        unread_reminders = Reminder.objects.filter(user=request.user, is_notified=False).order_by('-event_date')
        settings_obj, _ = MenstrualUserSetting.objects.get_or_create(user=request.user)
        
        # Get the base palette from color_theme choice
        theme_key = settings_obj.color_theme or MenstrualUserSetting.THEME_DEFAULT
        selected_palette = THEME_PALETTES.get(theme_key, THEME_PALETTES[MenstrualUserSetting.THEME_DEFAULT]).copy()
        
        # CRITICAL: Apply custom colors if use_custom_palette is enabled
        # This ensures colors are actually used on the frontend
        if settings_obj.use_custom_palette and settings_obj.custom_primary and settings_obj.custom_secondary:
            selected_palette['primary'] = settings_obj.custom_primary
            selected_palette['secondary'] = settings_obj.custom_secondary
            # Use secondary for accent too for color harmony
            selected_palette['accent'] = settings_obj.custom_secondary
            # Darken the on_color for better contrast on custom backgrounds
            selected_palette['on_color'] = '#0f172a'

        bg_style = settings_obj.background_style or MenstrualUserSetting.BG_LINEAR
        bg_intensity = settings_obj.background_intensity if settings_obj.background_intensity is not None else 24
        
        return {
            'unread_reminders': unread_reminders,
            'unread_reminders_count': unread_reminders.count(),
            'ui_color_theme': theme_key,
            'ui_palette': selected_palette,
            'ui_use_custom_palette': settings_obj.use_custom_palette,
            'ui_bg_style': bg_style,
            'ui_bg_intensity': bg_intensity,
        }
    
    return {
        'unread_reminders': [],
        'unread_reminders_count': 0,
        'ui_color_theme': theme_key,
        'ui_palette': selected_palette,
        'ui_use_custom_palette': False,
        'ui_bg_style': MenstrualUserSetting.BG_LINEAR,
        'ui_bg_intensity': 24,
    }