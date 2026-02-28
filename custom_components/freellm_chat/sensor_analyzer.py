"""Sensor analysis module for freellm_chat."""
from __future__ import annotations

import logging
from typing import Any
from statistics import mean, median, stdev
from datetime import datetime, timedelta
from collections import defaultdict

from homeassistant.core import HomeAssistant
from homeassistant.const import (
    STATE_ON, STATE_OFF, STATE_OPEN, STATE_CLOSED,
    STATE_HOME, STATE_NOT_HOME, STATE_UNAVAILABLE, STATE_UNKNOWN
)

_LOGGER = logging.getLogger(__name__)


class SensorAnalyzer:
    """Analyzer for comprehensive sensor data and statistics."""

    def __init__(self, hass: HomeAssistant, controlled_entities: dict[str, dict]) -> None:
        """Initialize the sensor analyzer."""
        self.hass = hass
        self.controlled_entities = controlled_entities

    # ========== TEMPERATUR ==========
    def analyze_temperatures(self) -> str:
        """Get detailed temperature readings from all rooms."""
        temps = {}
        
        for entity_id, info in self.controlled_entities.items():
            if info['domain'] != 'sensor':
                continue
                
            state = self.hass.states.get(entity_id)
            if not state:
                continue
            
            device_class = state.attributes.get('device_class')
            unit = state.attributes.get('unit_of_measurement', '')
            
            if device_class == 'temperature' or '°C' in unit or '°F' in unit:
                try:
                    temp_value = float(state.state)
                    area = info['area'] or 'Unbekannt'
                    
                    if area not in temps:
                        temps[area] = []
                    temps[area].append({
                        'name': info['name'],
                        'value': temp_value,
                        'unit': unit or '°C',
                        'entity_id': entity_id
                    })
                except (ValueError, TypeError):
                    continue
        
        if not temps:
            return "❌ Keine Temperatur-Sensoren gefunden"
        
        result = "🌡️ **TEMPERATUREN**\n\n"
        all_values = []
        warnings = []
        
        for area in sorted(temps.keys()):
            area_temps = temps[area]
            area_values = [t['value'] for t in area_temps]
            area_avg = mean(area_values)
            all_values.extend(area_values)
            
            # Bewertung
            if area_avg < 16:
                status = "🥶 Kalt"
                warnings.append(f"{area}: Zu kalt ({area_avg:.1f}°C)")
            elif area_avg < 19:
                status = "❄️ Kühl"
            elif area_avg <= 23:
                status = "✅ Optimal"
            elif area_avg <= 26:
                status = "☀️ Warm"
            else:
                status = "🔥 Heiß"
                warnings.append(f"{area}: Zu warm ({area_avg:.1f}°C)")
            
            result += f"📍 **{area}** {status}\n"
            for sensor in sorted(area_temps, key=lambda x: x['value'], reverse=True):
                result += f"   • {sensor['name']}: {sensor['value']:.1f}{sensor['unit']}\n"
            
            if len(area_temps) > 1:
                result += f"   📊 Durchschnitt: {area_avg:.1f}°C\n"
            result += "\n"
        
        # Gesamtstatistik
        result += "═══════════════════════════\n"
        result += "📊 **STATISTIK:**\n"
        result += f"   • Durchschnitt: {mean(all_values):.1f}°C\n"
        result += f"   • Minimum: {min(all_values):.1f}°C\n"
        result += f"   • Maximum: {max(all_values):.1f}°C\n"
        result += f"   • Differenz: {max(all_values) - min(all_values):.1f}°C\n"
        
        if len(all_values) > 2:
            result += f"   • Median: {median(all_values):.1f}°C\n"
            try:
                result += f"   • Std.Abw.: {stdev(all_values):.2f}°C\n"
            except:
                pass
        
        result += f"   • Sensoren: {len(all_values)}\n"
        
        if warnings:
            result += "\n⚠️ **WARNUNGEN:**\n"
            for w in warnings:
                result += f"   • {w}\n"
        
        return result

    # ========== LUFTFEUCHTIGKEIT ==========
    def analyze_humidity(self) -> str:
        """Get detailed humidity readings from all rooms."""
        humidity = {}
        
        for entity_id, info in self.controlled_entities.items():
            if info['domain'] != 'sensor':
                continue
                
            state = self.hass.states.get(entity_id)
            if not state:
                continue
            
            device_class = state.attributes.get('device_class')
            name_lower = info['name'].lower()
            
            if device_class == 'humidity' or any(w in name_lower for w in ['feucht', 'humidity', 'luftfeuchte', 'rh']):
                try:
                    value = float(state.state)
                    if value > 100:
                        continue  # Keine gültige Luftfeuchtigkeit
                    
                    area = info['area'] or 'Unbekannt'
                    
                    if area not in humidity:
                        humidity[area] = []
                    humidity[area].append({
                        'name': info['name'],
                        'value': value,
                        'entity_id': entity_id
                    })
                except (ValueError, TypeError):
                    continue
        
        if not humidity:
            return "❌ Keine Luftfeuchtigkeits-Sensoren gefunden"
        
        result = "💧 **LUFTFEUCHTIGKEIT**\n\n"
        all_values = []
        warnings = []
        
        for area in sorted(humidity.keys()):
            area_values = [h['value'] for h in humidity[area]]
            area_avg = mean(area_values)
            all_values.extend(area_values)
            
            # Bewertung
            if area_avg < 30:
                status = "⚠️ Zu trocken"
                warnings.append(f"{area}: Zu trocken ({area_avg:.0f}%) - Luftbefeuchter empfohlen")
            elif area_avg < 40:
                status = "🔸 Etwas trocken"
            elif area_avg <= 60:
                status = "✅ Optimal"
            elif area_avg <= 70:
                status = "🔸 Etwas feucht"
            else:
                status = "⚠️ Zu feucht"
                warnings.append(f"{area}: Zu feucht ({area_avg:.0f}%) - Lüften empfohlen")
            
            result += f"📍 **{area}** {status}\n"
            for sensor in humidity[area]:
                result += f"   • {sensor['name']}: {sensor['value']:.0f}%\n"
            result += "\n"
        
        # Statistik
        result += "═══════════════════════════\n"
        result += "📊 **STATISTIK:**\n"
        avg = mean(all_values)
        result += f"   • Durchschnitt: {avg:.0f}%"
        
        if avg < 30:
            result += " ⚠️ Zu trocken!\n"
        elif avg > 60:
            result += " ⚠️ Zu feucht!\n"
        else:
            result += " ✓ OK\n"
        
        result += f"   • Minimum: {min(all_values):.0f}%\n"
        result += f"   • Maximum: {max(all_values):.0f}%\n"
        result += f"   • Sensoren: {len(all_values)}\n"
        
        if warnings:
            result += "\n⚠️ **WARNUNGEN:**\n"
            for w in warnings:
                result += f"   • {w}\n"
        
        return result

    # ========== FENSTER & TÜREN ==========
    def check_open_windows(self) -> str:
        """Check which windows/doors are open with details."""
        items = {'windows': [], 'doors': [], 'garage': [], 'other': []}
        closed_count = {'windows': 0, 'doors': 0, 'garage': 0, 'other': 0}
        
        for entity_id, info in self.controlled_entities.items():
            if info['domain'] != 'binary_sensor':
                continue
                
            state = self.hass.states.get(entity_id)
            if not state:
                continue
            
            device_class = state.attributes.get('device_class')
            name = info['name']
            name_lower = name.lower()
            area = info['area'] or 'Unbekannt'
            is_open = state.state == STATE_ON
            
            # Kategorisierung
            if device_class == 'window' or any(w in name_lower for w in ['fenster', 'window']):
                category = 'windows'
            elif device_class == 'garage_door' or any(w in name_lower for w in ['garage', 'tor']):
                category = 'garage'
            elif device_class == 'door' or any(w in name_lower for w in ['tür', 'door', 'haustür', 'eingang']):
                category = 'doors'
            elif device_class in ['opening']:
                category = 'other'
            else:
                continue
            
            if is_open:
                # Berechne wie lange offen
                last_changed = state.last_changed
                duration = datetime.now(last_changed.tzinfo) - last_changed
                
                items[category].append({
                    'name': name,
                    'area': area,
                    'duration': duration
                })
            else:
                closed_count[category] += 1
        
        # Formatiere Ausgabe
        result = "🪟 **TÜREN & FENSTER**\n\n"
        
        total_open = sum(len(v) for v in items.values())
        total_closed = sum(closed_count.values())
        
        if total_open == 0:
            result += "✅ **Alles geschlossen!**\n\n"
            result += f"   • {closed_count['windows']} Fenster geschlossen\n"
            result += f"   • {closed_count['doors']} Türen geschlossen\n"
            if closed_count['garage'] > 0:
                result += f"   • {closed_count['garage']} Garagentore geschlossen\n"
            return result
        
        # Offene Fenster
        if items['windows']:
            result += f"🪟 **Offene Fenster ({len(items['windows'])}):**\n"
            for item in sorted(items['windows'], key=lambda x: x['duration'], reverse=True):
                duration_str = self._format_duration(item['duration'])
                result += f"   ⚠️ {item['name']} ({item['area']}) - seit {duration_str}\n"
            result += "\n"
        
        # Offene Türen
        if items['doors']:
            result += f"🚪 **Offene Türen ({len(items['doors'])}):**\n"
            for item in sorted(items['doors'], key=lambda x: x['duration'], reverse=True):
                duration_str = self._format_duration(item['duration'])
                result += f"   ⚠️ {item['name']} ({item['area']}) - seit {duration_str}\n"
            result += "\n"
        
        # Garage
        if items['garage']:
            result += f"🚗 **Offene Garagentore ({len(items['garage'])}):**\n"
            for item in items['garage']:
                duration_str = self._format_duration(item['duration'])
                result += f"   ⚠️ {item['name']} - seit {duration_str}\n"
            result += "\n"
        
        # Zusammenfassung
        result += "═══════════════════════════\n"
        result += f"📊 **GESAMT:** {total_open} offen, {total_closed} geschlossen\n"
        
        if total_open > 0:
            result += f"\n⚠️ **ACHTUNG:** {total_open} Öffnung(en) - Heizkosten/Sicherheit!"
        
        return result

    # ========== EINGESCHALTETE GERÄTE ==========
    def get_powered_on_devices(self) -> str:
        """Get all devices that are currently on with details."""
        on_devices = defaultdict(lambda: defaultdict(list))
        off_count = defaultdict(int)
        power_consumption = []
        
        domain_info = {
            'light': {'icon': '💡', 'name': 'Lichter'},
            'switch': {'icon': '🔌', 'name': 'Schalter'},
            'climate': {'icon': '🌡️', 'name': 'Klima'},
            'media_player': {'icon': '🔊', 'name': 'Media'},
            'fan': {'icon': '🌀', 'name': 'Ventilatoren'},
            'cover': {'icon': '🪟', 'name': 'Jalousien'},
            'vacuum': {'icon': '🧹', 'name': 'Staubsauger'},
        }
        
        for entity_id, info in self.controlled_entities.items():
            state = self.hass.states.get(entity_id)
            if not state:
                continue
            
            domain = info['domain']
            if domain not in domain_info:
                continue
            
            is_on = False
            extra_info = []
            
            if domain == 'light':
                is_on = state.state == STATE_ON
                if is_on:
                    brightness = state.attributes.get('brightness')
                    if brightness:
                        pct = int(brightness / 255 * 100)
                        extra_info.append(f"{pct}%")
                    rgb = state.attributes.get('rgb_color')
                    if rgb:
                        extra_info.append(f"RGB:{rgb}")
                        
            elif domain == 'switch':
                is_on = state.state == STATE_ON
                power = state.attributes.get('current_power_w')
                if power:
                    extra_info.append(f"{power}W")
                    power_consumption.append(power)
                    
            elif domain == 'climate':
                is_on = state.state not in ['off', STATE_UNAVAILABLE, STATE_UNKNOWN]
                if is_on:
                    temp = state.attributes.get('temperature')
                    current = state.attributes.get('current_temperature')
                    mode = state.state
                    if temp:
                        extra_info.append(f"Ziel:{temp}°C")
                    if current:
                        extra_info.append(f"Aktuell:{current}°C")
                    extra_info.append(f"[{mode}]")
                    
            elif domain == 'media_player':
                is_on = state.state in ['playing', 'paused', 'on', 'idle']
                if is_on:
                    title = state.attributes.get('media_title')
                    source = state.attributes.get('source')
                    if title:
                        extra_info.append(f'"{title[:20]}"')
                    elif source:
                        extra_info.append(source)
                    extra_info.append(f"[{state.state}]")
                    
            elif domain == 'fan':
                is_on = state.state == STATE_ON
                speed = state.attributes.get('percentage')
                if speed:
                    extra_info.append(f"{speed}%")
                    
            elif domain == 'cover':
                is_on = state.state not in [STATE_CLOSED, 'closed']
                pos = state.attributes.get('current_position')
                if pos is not None:
                    extra_info.append(f"Position:{pos}%")
                    
            elif domain == 'vacuum':
                is_on = state.state in ['cleaning', 'returning']
                if is_on:
                    extra_info.append(f"[{state.state}]")
            
            if is_on:
                area = info['area'] or 'Unbekannt'
                on_devices[domain][area].append({
                    'name': info['name'],
                    'extra': ' '.join(extra_info) if extra_info else ''
                })
            else:
                off_count[domain] += 1
        
        # Formatiere Ausgabe
        result = "⚡ **EINGESCHALTETE GERÄTE**\n\n"
        
        total_on = sum(sum(len(devices) for devices in areas.values()) for areas in on_devices.values())
        total_off = sum(off_count.values())
        
        if total_on == 0:
            result += "✅ **Alle Geräte ausgeschaltet!**\n\n"
            for domain, count in sorted(off_count.items()):
                if count > 0:
                    info = domain_info.get(domain, {'icon': '📦', 'name': domain})
                    result += f"   {info['icon']} {count} {info['name']} aus\n"
            return result
        
        for domain in ['light', 'switch', 'climate', 'media_player', 'fan', 'cover', 'vacuum']:
            if domain not in on_devices:
                continue
            
            info = domain_info[domain]
            device_count = sum(len(devices) for devices in on_devices[domain].values())
            
            result += f"{info['icon']} **{info['name']} ({device_count} an):**\n"
            
            for area in sorted(on_devices[domain].keys()):
                result += f"   📍 {area}:\n"
                for device in on_devices[domain][area]:
                    if device['extra']:
                        result += f"      • {device['name']} {device['extra']}\n"
                    else:
                        result += f"      • {device['name']}\n"
            result += "\n"
        
        # Zusammenfassung
        result += "═══════════════════════════\n"
        result += f"📊 **GESAMT:** {total_on} an, {total_off} aus\n"
        
        if power_consumption:
            total_power = sum(power_consumption)
            result += f"⚡ **Stromverbrauch:** {total_power:.1f}W\n"
        
        return result

    # ========== BATTERIE-STATUS ==========
    def check_battery_status(self) -> str:
        """Check detailed battery status of all devices."""
        batteries = {'critical': [], 'low': [], 'medium': [], 'good': [], 'full': [], 'unavailable': []}
        
        for entity_id, info in self.controlled_entities.items():
            if info['domain'] != 'sensor':
                continue
            
            state = self.hass.states.get(entity_id)
            if not state:
                continue
            
            device_class = state.attributes.get('device_class')
            name = info['name']
            name_lower = name.lower()
            
            if device_class == 'battery' or 'battery' in name_lower or 'batterie' in name_lower or 'akku' in name_lower:
                area = info['area'] or 'Unbekannt'
                
                if state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN]:
                    batteries['unavailable'].append({'name': name, 'area': area})
                    continue
                
                try:
                    level = float(state.state)
                    entry = {'name': name, 'area': area, 'level': level}
                    
                    if level < 10:
                        batteries['critical'].append(entry)
                    elif level < 20:
                        batteries['low'].append(entry)
                    elif level < 50:
                        batteries['medium'].append(entry)
                    elif level < 90:
                        batteries['good'].append(entry)
                    else:
                        batteries['full'].append(entry)
                        
                except (ValueError, TypeError):
                    batteries['unavailable'].append({'name': name, 'area': area})
        
        total = sum(len(v) for v in batteries.values())
        
        if total == 0:
            return "❌ Keine Batterie-Sensoren gefunden"
        
        result = "🔋 **BATTERIE-STATUS**\n\n"
        
        # Kritisch
        if batteries['critical']:
            result += f"🔴 **KRITISCH (<10%) - {len(batteries['critical'])} Gerät(e):**\n"
            for b in sorted(batteries['critical'], key=lambda x: x['level']):
                result += f"   ⚠️ {b['name']} ({b['area']}): {b['level']:.0f}% - SOFORT WECHSELN!\n"
            result += "\n"
        
        # Niedrig
        if batteries['low']:
            result += f"🟠 **Niedrig (10-20%) - {len(batteries['low'])} Gerät(e):**\n"
            for b in sorted(batteries['low'], key=lambda x: x['level']):
                result += f"   ⚡ {b['name']} ({b['area']}): {b['level']:.0f}%\n"
            result += "\n"
        
        # Mittel
        if batteries['medium']:
            result += f"🟡 **Mittel (20-50%) - {len(batteries['medium'])} Gerät(e):**\n"
            for b in sorted(batteries['medium'], key=lambda x: x['level'])[:5]:
                result += f"   • {b['name']} ({b['area']}): {b['level']:.0f}%\n"
            if len(batteries['medium']) > 5:
                result += f"   ... und {len(batteries['medium']) - 5} weitere\n"
            result += "\n"
        
        # Gut
        if batteries['good']:
            result += f"🟢 **Gut (50-90%) - {len(batteries['good'])} Gerät(e):**\n"
            for b in sorted(batteries['good'], key=lambda x: x['level'])[:3]:
                result += f"   ✓ {b['name']}: {b['level']:.0f}%\n"
            if len(batteries['good']) > 3:
                result += f"   ... und {len(batteries['good']) - 3} weitere OK\n"
            result += "\n"
        
        # Voll
        if batteries['full']:
            result += f"✅ **Voll (>90%) - {len(batteries['full'])} Gerät(e)**\n\n"
        
        # Statistik
        all_levels = []
        for cat in ['critical', 'low', 'medium', 'good', 'full']:
            all_levels.extend([b['level'] for b in batteries[cat]])
        
        result += "═══════════════════════════\n"
        result += "📊 **STATISTIK:**\n"
        result += f"   • Durchschnitt: {mean(all_levels):.0f}%\n"
        result += f"   • Niedrigster: {min(all_levels):.0f}%\n"
        result += f"   • Sensoren: {len(all_levels)}\n"
        
        critical_count = len(batteries['critical']) + len(batteries['low'])
        if critical_count > 0:
            result += f"\n🚨 **{critical_count} Batterie(n) müssen bald gewechselt werden!**"
        
        return result

    # ========== OFFLINE GERÄTE ==========
    def check_offline_devices(self) -> str:
        """Check for offline/unavailable devices with details."""
        offline = []
        online_count = 0
        
        for entity_id, info in self.controlled_entities.items():
            state = self.hass.states.get(entity_id)
            
            if not state:
                offline.append({
                    'name': info['name'],
                    'area': info['area'] or 'Unbekannt',
                    'domain': info['domain'],
                    'entity_id': entity_id,
                    'reason': 'Keine State-Daten',
                    'duration': None
                })
                continue
            
            if state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN]:
                last_changed = state.last_changed
                duration = datetime.now(last_changed.tzinfo) - last_changed
                
                offline.append({
                    'name': info['name'],
                    'area': info['area'] or 'Unbekannt',
                    'domain': info['domain'],
                    'entity_id': entity_id,
                    'state': state.state,
                    'duration': duration
                })
            else:
                online_count += 1
        
        result = "📵 **GERÄTE-VERFÜGBARKEIT**\n\n"
        
        if not offline:
            result += f"✅ **Alle {online_count} Geräte online!**\n"
            return result
        
        result += f"⚠️ **{len(offline)} Gerät(e) offline/nicht verfügbar:**\n\n"
        
        # Gruppiere nach Bereich
        by_area = defaultdict(list)
        for device in offline:
            by_area[device['area']].append(device)
        
        domain_icons = {
            'light': '💡', 'switch': '🔌', 'sensor': '📊',
            'binary_sensor': '⚡', 'climate': '🌡️'
        }
        
        for area in sorted(by_area.keys()):
            result += f"📍 **{area}:**\n"
            for device in sorted(by_area[area], key=lambda x: x['name']):
                icon = domain_icons.get(device['domain'], '📦')
                result += f"   {icon} {device['name']}\n"
                
                if device['duration']:
                    duration_str = self._format_duration(device['duration'])
                    result += f"      Offline seit: {duration_str}\n"
                
                result += f"      ID: {device['entity_id']}\n"
            result += "\n"
        
        # Zusammenfassung
        result += "═══════════════════════════\n"
        result += f"📊 **GESAMT:** {online_count} online, {len(offline)} offline\n"
        
        # Lange offline Warnung
        long_offline = [d for d in offline if d['duration'] and d['duration'].days > 1]
        if long_offline:
            result += f"\n🚨 **{len(long_offline)} Gerät(e) länger als 1 Tag offline!**"
        
        return result

    # ========== ENERGIE-VERBRAUCH ==========
    def analyze_energy(self) -> str:
        """Analyze energy consumption."""
        energy_sensors = {'power': [], 'energy': [], 'voltage': [], 'current': []}
        
        for entity_id, info in self.controlled_entities.items():
            if info['domain'] != 'sensor':
                continue
                
            state = self.hass.states.get(entity_id)
            if not state:
                continue
            
            device_class = state.attributes.get('device_class')
            unit = state.attributes.get('unit_of_measurement', '')
            
            try:
                value = float(state.state)
                entry = {
                    'name': info['name'],
                    'area': info['area'] or 'Unbekannt',
                    'value': value,
                    'unit': unit
                }
                
                if device_class == 'power' or 'W' in unit:
                    energy_sensors['power'].append(entry)
                elif device_class == 'energy' or 'kWh' in unit or 'Wh' in unit:
                    energy_sensors['energy'].append(entry)
                elif device_class == 'voltage' or 'V' in unit:
                    energy_sensors['voltage'].append(entry)
                elif device_class == 'current' or 'A' in unit:
                    energy_sensors['current'].append(entry)
                    
            except (ValueError, TypeError):
                continue
        
        total_sensors = sum(len(v) for v in energy_sensors.values())
        
        if total_sensors == 0:
            return "❌ Keine Energie-Sensoren gefunden"
        
        result = "⚡ **ENERGIE-VERBRAUCH**\n\n"
        
        # Aktuelle Leistung
        if energy_sensors['power']:
            result += "🔌 **Aktuelle Leistung:**\n"
            total_power = 0
            
            for sensor in sorted(energy_sensors['power'], key=lambda x: x['value'], reverse=True):
                result += f"   • {sensor['name']}: {sensor['value']:.1f}{sensor['unit']}\n"
                if 'W' in sensor['unit'] and 'k' not in sensor['unit'].lower():
                    total_power += sensor['value']
                elif 'kW' in sensor['unit']:
                    total_power += sensor['value'] * 1000
            
            result += f"\n   📊 **Gesamt: {total_power:.0f}W**\n"
            
            # Kosten-Schätzung (0.30€/kWh)
            cost_per_hour = total_power / 1000 * 0.30
            cost_per_day = cost_per_hour * 24
            result += f"   💰 Geschätzte Kosten: {cost_per_hour:.3f}€/h ({cost_per_day:.2f}€/Tag)\n\n"
        
        # Energieverbrauch
        if energy_sensors['energy']:
            result += "📊 **Energie-Zähler:**\n"
            for sensor in sorted(energy_sensors['energy'], key=lambda x: x['value'], reverse=True)[:10]:
                result += f"   • {sensor['name']}: {sensor['value']:.2f} {sensor['unit']}\n"
            result += "\n"
        
        # Spannung
        if energy_sensors['voltage']:
            result += "⚡ **Spannung:**\n"
            for sensor in energy_sensors['voltage'][:3]:
                result += f"   • {sensor['name']}: {sensor['value']:.1f}{sensor['unit']}\n"
            result += "\n"
        
        return result

    # ========== KLIMA-ÜBERSICHT ==========
    def get_climate_overview(self) -> str:
        """Get overview of all climate/HVAC systems."""
        climate_devices = []
        
        for entity_id, info in self.controlled_entities.items():
            if info['domain'] != 'climate':
                continue
            
            state = self.hass.states.get(entity_id)
            if not state:
                continue
            
            climate_devices.append({
                'name': info['name'],
                'area': info['area'] or 'Unbekannt',
                'state': state.state,
                'current_temp': state.attributes.get('current_temperature'),
                'target_temp': state.attributes.get('temperature'),
                'hvac_mode': state.attributes.get('hvac_mode'),
                'hvac_action': state.attributes.get('hvac_action'),
                'preset': state.attributes.get('preset_mode'),
            })
        
        if not climate_devices:
            return "❌ Keine Klimageräte gefunden"
        
        result = "🌡️ **KLIMA-ÜBERSICHT**\n\n"
        
        active_count = sum(1 for d in climate_devices if d['state'] not in ['off', STATE_UNAVAILABLE])
        result += f"📊 {active_count} von {len(climate_devices)} Geräten aktiv\n\n"
        
        for device in sorted(climate_devices, key=lambda x: x['area']):
            mode_icon = '🔥' if device['state'] == 'heat' else '❄️' if device['state'] == 'cool' else '💨' if device['state'] == 'fan_only' else '⭕' if device['state'] == 'off' else '🌀'
            
            result += f"{mode_icon} **{device['name']}** ({device['area']})\n"
            result += f"   Modus: {device['state']}\n"
            
            if device['current_temp']:
                result += f"   Aktuell: {device['current_temp']}°C\n"
            if device['target_temp']:
                result += f"   Ziel: {device['target_temp']}°C\n"
            if device['hvac_action']:
                result += f"   Aktion: {device['hvac_action']}\n"
            if device['preset']:
                result += f"   Preset: {device['preset']}\n"
            result += "\n"
        
        return result

    # ========== BEWEGUNGSSENSOREN ==========
    def check_motion_sensors(self) -> str:
        """Check motion sensor status and last activity."""
        motion_sensors = []
        
        for entity_id, info in self.controlled_entities.items():
            if info['domain'] != 'binary_sensor':
                continue
            
            state = self.hass.states.get(entity_id)
            if not state:
                continue
            
            device_class = state.attributes.get('device_class')
            name_lower = info['name'].lower()
            
            if device_class in ['motion', 'occupancy', 'presence'] or any(w in name_lower for w in ['bewegung', 'motion', 'presence', 'präsenz']):
                last_changed = state.last_changed
                duration = datetime.now(last_changed.tzinfo) - last_changed
                
                motion_sensors.append({
                    'name': info['name'],
                    'area': info['area'] or 'Unbekannt',
                    'is_active': state.state == STATE_ON,
                    'last_changed': last_changed,
                    'duration': duration
                })
        
        if not motion_sensors:
            return "❌ Keine Bewegungssensoren gefunden"
        
        result = "🏃 **BEWEGUNGSSENSOREN**\n\n"
        
        # Aktive Bewegung
        active = [s for s in motion_sensors if s['is_active']]
        inactive = [s for s in motion_sensors if not s['is_active']]
        
        if active:
            result += f"🔴 **Aktive Bewegung ({len(active)}):**\n"
            for sensor in sorted(active, key=lambda x: x['duration']):
                duration_str = self._format_duration(sensor['duration'])
                result += f"   🏃 {sensor['name']} ({sensor['area']}) - seit {duration_str}\n"
            result += "\n"
        
        # Letzte Aktivität
        result += f"⚪ **Keine Bewegung ({len(inactive)}):**\n"
        for sensor in sorted(inactive, key=lambda x: x['duration'])[:5]:
            duration_str = self._format_duration(sensor['duration'])
            result += f"   • {sensor['name']} ({sensor['area']}) - zuletzt vor {duration_str}\n"
        
        if len(inactive) > 5:
            result += f"   ... und {len(inactive) - 5} weitere\n"
        
        return result

    # ========== LUFTQUALITÄT ==========
    def analyze_air_quality(self) -> str:
        """Analyze air quality sensors."""
        air_sensors = {'co2': [], 'pm25': [], 'pm10': [], 'voc': [], 'aqi': []}
        
        for entity_id, info in self.controlled_entities.items():
            if info['domain'] != 'sensor':
                continue
            
            state = self.hass.states.get(entity_id)
            if not state:
                continue
            
            device_class = state.attributes.get('device_class')
            name_lower = info['name'].lower()
            unit = state.attributes.get('unit_of_measurement', '')
            
            try:
                value = float(state.state)
                entry = {
                    'name': info['name'],
                    'area': info['area'] or 'Unbekannt',
                    'value': value,
                    'unit': unit
                }
                
                if device_class == 'carbon_dioxide' or 'co2' in name_lower:
                    air_sensors['co2'].append(entry)
                elif device_class == 'pm25' or 'pm2.5' in name_lower or 'pm25' in name_lower:
                    air_sensors['pm25'].append(entry)
                elif device_class == 'pm10' or 'pm10' in name_lower:
                    air_sensors['pm10'].append(entry)
                elif 'voc' in name_lower or 'tvoc' in name_lower:
                    air_sensors['voc'].append(entry)
                elif device_class == 'aqi' or 'luftqualität' in name_lower or 'air quality' in name_lower:
                    air_sensors['aqi'].append(entry)
                    
            except (ValueError, TypeError):
                continue
        
        total = sum(len(v) for v in air_sensors.values())
        
        if total == 0:
            return "❌ Keine Luftqualitäts-Sensoren gefunden"
        
        result = "🌬️ **LUFTQUALITÄT**\n\n"
        
        # CO2
        if air_sensors['co2']:
            result += "💨 **CO2-Werte:**\n"
            for sensor in sorted(air_sensors['co2'], key=lambda x: x['value'], reverse=True):
                value = sensor['value']
                if value < 800:
                    status = "✅ Sehr gut"
                elif value < 1000:
                    status = "✓ Gut"
                elif value < 1500:
                    status = "⚠️ Mäßig - Lüften empfohlen"
                else:
                    status = "🔴 Schlecht - Sofort lüften!"
                
                result += f"   • {sensor['name']} ({sensor['area']}): {value:.0f} {sensor['unit']} - {status}\n"
            result += "\n"
        
        # Feinstaub PM2.5
        if air_sensors['pm25']:
            result += "🌫️ **Feinstaub PM2.5:**\n"
            for sensor in air_sensors['pm25']:
                value = sensor['value']
                if value < 10:
                    status = "✅ Sehr gut"
                elif value < 25:
                    status = "✓ Gut"
                elif value < 50:
                    status = "⚠️ Mäßig"
                else:
                    status = "🔴 Schlecht"
                
                result += f"   • {sensor['name']}: {value:.1f} {sensor['unit']} - {status}\n"
            result += "\n"
        
        # VOC
        if air_sensors['voc']:
            result += "🧪 **VOC (Flüchtige Verbindungen):**\n"
            for sensor in air_sensors['voc']:
                result += f"   • {sensor['name']}: {sensor['value']:.0f} {sensor['unit']}\n"
            result += "\n"
        
        return result

    # ========== ALLE SENSOREN ==========
    def get_all_sensors_summary(self) -> str:
        """Get summary of all sensor readings."""
        sensors_by_type = defaultdict(list)
        
        for entity_id, info in self.controlled_entities.items():
            if info['domain'] not in ['sensor', 'binary_sensor']:
                continue
            
            state = self.hass.states.get(entity_id)
            if not state:
                continue
            
            device_class = state.attributes.get('device_class', 'unknown')
            
            sensors_by_type[device_class].append({
                'name': info['name'],
                'area': info['area'],
                'state': state.state,
                'unit': state.attributes.get('unit_of_measurement', '')
            })
        
        result = "📊 **SENSOR-ÜBERSICHT**\n\n"
        
        for device_class in sorted(sensors_by_type.keys()):
            sensors = sensors_by_type[device_class]
            result += f"**{device_class.title()}** ({len(sensors)}):\n"
            
            for sensor in sorted(sensors, key=lambda x: x['name'])[:5]:
                result += f"   • {sensor['name']}: {sensor['state']}{sensor['unit']}\n"
            
            if len(sensors) > 5:
                result += f"   ... und {len(sensors) - 5} weitere\n"
            result += "\n"
        
        result += f"📊 **Gesamt:** {sum(len(v) for v in sensors_by_type.values())} Sensoren\n"
        
        return result

    # ========== GERÄTE-ZUSAMMENFASSUNG ==========
    def get_device_summary(self) -> str:
        """Get comprehensive device summary."""
        summary = {
            'total': len(self.controlled_entities),
            'by_domain': defaultdict(int),
            'by_area': defaultdict(int),
            'online': 0,
            'offline': 0,
            'on': 0,
            'off': 0
        }
        
        for entity_id, info in self.controlled_entities.items():
            state = self.hass.states.get(entity_id)
            
            summary['by_domain'][info['domain']] += 1
            summary['by_area'][info['area'] or 'Ohne Bereich'] += 1
            
            if state:
                if state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN]:
                    summary['offline'] += 1
                else:
                    summary['online'] += 1
                    if state.state == STATE_ON:
                        summary['on'] += 1
                    elif state.state == STATE_OFF:
                        summary['off'] += 1
        
        result = "📱 **GERÄTE-ZUSAMMENFASSUNG**\n\n"
        
        result += f"📊 **Gesamt:** {summary['total']} Geräte\n"
        result += f"   ✅ Online: {summary['online']}\n"
        result += f"   ❌ Offline: {summary['offline']}\n"
        result += f"   💡 An: {summary['on']}\n"
        result += f"   ⭕ Aus: {summary['off']}\n\n"
        
        result += "**Nach Typ:**\n"
        domain_icons = {
            'light': '💡', 'switch': '🔌', 'sensor': '📊',
            'binary_sensor': '⚡', 'climate': '🌡️', 'cover': '🪟',
            'media_player': '🔊', 'fan': '🌀'
        }
        for domain, count in sorted(summary['by_domain'].items(), key=lambda x: -x[1]):
            icon = domain_icons.get(domain, '📦')
            result += f"   {icon} {domain}: {count}\n"
        
        result += "\n**Nach Bereich:**\n"
        for area, count in sorted(summary['by_area'].items(), key=lambda x: -x[1]):
            result += f"   📍 {area}: {count}\n"
        
        return result

    # ========== LETZTE AKTIVITÄTEN ==========
    def get_last_activities(self) -> str:
        """Get last activities/changes."""
        activities = []
        
        for entity_id, info in self.controlled_entities.items():
            state = self.hass.states.get(entity_id)
            if not state:
                continue
            
            activities.append({
                'name': info['name'],
                'area': info['area'],
                'domain': info['domain'],
                'state': state.state,
                'last_changed': state.last_changed
            })
        
        # Sortiere nach Zeit
        activities.sort(key=lambda x: x['last_changed'], reverse=True)
        
        result = "🕐 **LETZTE AKTIVITÄTEN**\n\n"
        
        now = datetime.now(activities[0]['last_changed'].tzinfo) if activities else datetime.now()
        
        for activity in activities[:15]:
            duration = now - activity['last_changed']
            duration_str = self._format_duration(duration)
            
            result += f"• **{activity['name']}**"
            if activity['area']:
                result += f" ({activity['area']})"
            result += f"\n   {activity['state']} - vor {duration_str}\n"
        
        if len(activities) > 15:
            result += f"\n... und {len(activities) - 15} weitere Geräte"
        
        return result

    # ========== HILFSFUNKTIONEN ==========
    def _format_duration(self, duration: timedelta) -> str:
        """Format duration to human readable string."""
        total_seconds = duration.total_seconds()
        
        if total_seconds < 60:
            return f"{int(total_seconds)} Sek."
        elif total_seconds < 3600:
            return f"{int(total_seconds / 60)} Min."
        elif total_seconds < 86400:
            hours = int(total_seconds / 3600)
            minutes = int((total_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
        else:
            days = int(total_seconds / 86400)
            hours = int((total_seconds % 86400) / 3600)
            return f"{days}d {hours}h"