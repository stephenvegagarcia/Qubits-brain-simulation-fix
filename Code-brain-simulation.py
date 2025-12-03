import pygame
import numpy as np
import sys
import math
import random
from collections import deque
from qutip import *

# ==================== CONFIG ====================
WIDTH, HEIGHT = 1000, 600
BG_COLOR = (10, 10, 15)
PANEL_COLOR = (20, 20, 30)

# Colors
CONTROL_RED = (255, 60, 60)      # Unprotected Qubit
PROTECTED_CYAN = (0, 255, 255)   # Minus-Minus Protected
BRAIN_GREEN = (50, 255, 50)      # Raw Input
GAIN_GOLD = (255, 215, 0)        # Net Advantage

# ==================== 1. THE BRAIN SIMULATOR ====================
class BrainInterface:
    def __init__(self):
        print("MOBILE MODE: Using Pure Python Brain Simulator")
        self.time_step = 0.0
        self.stress_phase = 0.0

    def get_stress_level(self):
        self.time_step += 0.05
        
        # Base Rhythm
        base_wave = math.sin(self.time_step) * 0.3 + math.cos(self.time_step * 0.5) * 0.2
        
        # Noise
        noise = random.uniform(-0.1, 0.1)
        
        # Stress Events
        if random.random() < 0.02:
            self.stress_phase = 1.0
            
        # Decay
        if self.stress_phase > 0:
            self.stress_phase -= 0.02
        
        total_stress = 0.3 + (base_wave * 0.1) + self.stress_phase + noise
        return np.clip(total_stress, 0.0, 1.0)

# ==================== 2. THE QUANTUM SIMULATION ====================
class QuantumTestBench:
    def __init__(self):
        # Target: |+> state (Superposition)
        self.psi_target = (basis(2,0) + basis(2,1)).unit() 
        self.P_target = self.psi_target * self.psi_target.dag()
        
        # Operators for measurement
        self.sx = sigmax() # Measure X axis alignment
        
        # States
        self.rho_control = self.psi_target * self.psi_target.dag()
        self.rho_algo = self.psi_target * self.psi_target.dag()
        
        # Stats
        self.total_corrections = 0

    def evolve(self, stress_level):
        # Noise Strength
        noise_strength = stress_level * 0.15
        noise_op = sigmaz() # Phase Flip
        
        # 1. Damage the Control
        self.rho_control = (1 - noise_strength) * self.rho_control + \
                           noise_strength * noise_op * self.rho_control * noise_op.dag()
                           
        # 2. Damage the Algorithm State
        self.rho_algo = (1 - noise_strength) * self.rho_algo + \
                        noise_strength * noise_op * self.rho_algo * noise_op.dag()
        
        # 3. Check Fidelity
        fid_b = expect(self.P_target, self.rho_algo)
        
        correction_triggered = False
        if fid_b < 0.90: 
            correction_triggered = True
            self.total_corrections += 1
            # Zeno Correction
            self.rho_algo = 0.8 * self.rho_algo + 0.2 * self.P_target

        # 4. Gather Data
        fid_a = expect(self.P_target, self.rho_control)
        fid_b = expect(self.P_target, self.rho_algo)
        
        # Measure orientation on Bloch Sphere (X-axis projection)
        # 1.0 means perfectly aligned with Target, 0.0 means mixed, -1.0 means opposite
        align_a = expect(self.sx, self.rho_control)
        align_b = expect(self.sx, self.rho_algo)
        
        return fid_a, fid_b, correction_triggered, align_a, align_b

# ==================== VISUALIZATION ====================
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("MINUS-MINUS | Advanced Analytics")
clock = pygame.time.Clock()

font = pygame.font.SysFont('arial', 16)
font_lg = pygame.font.SysFont('arial', 24, bold=True)

brain = BrainInterface()
q_bench = QuantumTestBench()

# Data Containers
history_a = deque(maxlen=400)
history_b = deque(maxlen=400)
history_gain = deque(maxlen=400) # Added Gain tracking
history_stress = deque(maxlen=400)

def draw_bloch_projection(surface, x, y, size, align_a, align_b):
    """Draws a 2D projection of the qubit states"""
    # Background
    pygame.draw.circle(surface, (40, 40, 50), (x, y), size)
    pygame.draw.circle(surface, (100, 100, 100), (x, y), size, 1)
    
    # Target Marker (Right side)
    pygame.draw.line(surface, (255,255,255), (x, y), (x+size, y), 1)
    text = font.render("Target |+>", True, (150,150,150))
    surface.blit(text, (x+size+5, y-10))

    # Control State (Red Vector)
    # Mapping alignment (-1 to 1) to angle
    # Ideally X axis, but we simplify to 2D projection
    len_a = size * abs(align_a) # Shortens as it loses purity
    end_ax = x + (len_a * math.cos(0)) # Locked to X axis for this viz
    end_ay = y # It essentially shrinks towards center as it decoheres
    pygame.draw.circle(surface, CONTROL_RED, (int(x + align_a*size), y), 6)
    
    # Protected State (Cyan Vector)
    pygame.draw.circle(surface, PROTECTED_CYAN, (int(x + align_b*size), y), 8, 2)

while True:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            pygame.quit(); sys.exit()

    screen.fill(BG_COLOR)
    
    # 1. GET DATA
    stress = brain.get_stress_level()
    fid_a, fid_b, corrected, align_a, align_b = q_bench.evolve(stress)
    gain = fid_b - fid_a # Calculate Quantum Advantage
    
    history_a.append(fid_a)
    history_b.append(fid_b)
    history_gain.append(gain)
    history_stress.append(stress)
    
    # ================= DRAWING =================
    
    # --- MAIN GRAPH (Fidelity) ---
    graph_x, graph_y, graph_w, graph_h = 50, 150, 600, 300
    pygame.draw.rect(screen, PANEL_COLOR, (graph_x, graph_y, graph_w, graph_h))
    
    # Grid lines
    pygame.draw.line(screen, (50,50,60), (graph_x, graph_y + graph_h//2), (graph_x+graph_w, graph_y + graph_h//2))
    
    scale_x = graph_w / 400
    
    # Draw Gain Fill (Gold Area)
    if len(history_gain) > 1:
        pts_gain = []
        for i, val in enumerate(history_gain):
            x = graph_x + int(i * scale_x)
            # Scale gain (0.0 to 1.0) to fit nicely at bottom
            y = graph_y + graph_h - int(val * 100) 
            pts_gain.append((x,y))
        
        # Close the polygon for filling
        if len(pts_gain) > 2:
            pts_poly = pts_gain + [(pts_gain[-1][0], graph_y + graph_h), (pts_gain[0][0], graph_y + graph_h)]
            pygame.draw.polygon(screen, (50, 40, 10), pts_poly) # Dark gold background
    
    # Draw Lines
    pts_a = [(graph_x + int(i*scale_x), graph_y + graph_h - int(v*graph_h)) for i,v in enumerate(history_a)]
    pts_b = [(graph_x + int(i*scale_x), graph_y + graph_h - int(v*graph_h)) for i,v in enumerate(history_b)]
    pts_s = [(graph_x + int(i*scale_x), graph_y + graph_h - int(v*50)) for i,v in enumerate(history_stress)]
    
    if len(pts_a) > 1: pygame.draw.lines(screen, CONTROL_RED, False, pts_a, 2)
    if len(pts_b) > 1: pygame.draw.lines(screen, PROTECTED_CYAN, False, pts_b, 3)
    if len(pts_s) > 1: pygame.draw.lines(screen, BRAIN_GREEN, False, pts_s, 1)

    # --- SIDE PANEL (Analytics) ---
    panel_x = 700
    pygame.draw.rect(screen, PANEL_COLOR, (panel_x, 150, 250, 300))
    
    # Bloch Projection
    draw_bloch_projection(screen, panel_x + 125, 350, 60, align_a, align_b)
    
    # Text Stats
    screen.blit(font_lg.render("ALGORITHM STATUS", True, (200,200,200)), (50, 50))
    
    # Live Data
    screen.blit(font.render(f"CONTROL FIDELITY: {fid_a:.3f}", True, CONTROL_RED), (panel_x + 20, 170))
    screen.blit(font.render(f"PROTECTED FIDELITY: {fid_b:.3f}", True, PROTECTED_CYAN), (panel_x + 20, 200))
    
    # Calculated Metrics
    screen.blit(font.render(f"NET QUANTUM GAIN: +{gain:.3f}", True, GAIN_GOLD), (panel_x + 20, 240))
    screen.blit(font.render(f"TOTAL CORRECTIONS: {q_bench.total_corrections}", True, (150,150,255)), (panel_x + 20, 270))
    
    # Status Indicator
    if corrected:
        pygame.draw.circle(screen, PROTECTED_CYAN, (WIDTH-50, 50), 10)
        screen.blit(font.render("CORRECTING...", True, PROTECTED_CYAN), (WIDTH-180, 42))

    # Graph Labels
    screen.blit(font.render("1.0", True, (100,100,100)), (20, 150))
    screen.blit(font.render("0.0", True, (100,100,100)), (20, 150+300-10))

    pygame.display.flip()
    clock.tick(30)
