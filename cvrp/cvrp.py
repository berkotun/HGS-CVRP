import streamlit as st
import numpy as np
import random
import math
from typing import List, Tuple, Dict
import time
import warnings
import matplotlib.pyplot as plt
import os
warnings.filterwarnings('ignore')

class CVRPSolver:
    """HGS-CVRP v9.1 - ULTRA OPTİMİZE"""

    def __init__(self, vrp_file):
        self.nodes = []
        self.demands = {}
        self.capacity = 0
        self.problem_name = ""
        self.best_solution = None
        self.best_cost = float('inf')
        self.convergence_history = []
        self.execution_time = 0
        self.distance_cache = {}
        self.iteration_count = 0
        self.parse_vrp_file(vrp_file)

    def parse_vrp_file(self, filename):
        with open(filename, 'r') as f:
            lines = f.readlines()

        section = ""
        coordinates = {}

        for line in lines:
            line = line.strip()
            if not line or line.startswith('COMMENT'):
                continue
            if 'NAME' in line:
                self.problem_name = line.split(':')[1].strip()
            elif 'DIMENSION' in line:
                self.dimension = int(line.split(':')[1])
            elif 'CAPACITY' in line:
                self.capacity = int(line.split(':')[1])
            elif 'NODE_COORD_SECTION' in line:
                section = 'coords'
            elif 'DEMAND_SECTION' in line:
                section = 'demands'
            elif 'DEPOT_SECTION' in line or 'EOF' in line:
                section = ''
            elif section == 'coords' and line:
                parts = line.split()
                if len(parts) == 3:
                    coordinates[int(parts[0])] = (int(parts[1]), int(parts[2]))
            elif section == 'demands' and line:
                parts = line.split()
                if len(parts) == 2:
                    self.demands[int(parts[0])] = int(parts[1])

        for node_id in sorted(coordinates.keys()):
            x, y = coordinates[node_id]
            self.nodes.append({
                'id': node_id,
                'x': x,
                'y': y,
                'demand': self.demands.get(node_id, 0),
                'is_depot': (node_id == 1)
            })

    def euclidean_distance(self, node1, node2):
        key = (node1['id'], node2['id'])
        if key not in self.distance_cache:
            dist = math.sqrt((node1['x'] - node2['x'])**2 + (node1['y'] - node2['y'])**2)
            self.distance_cache[key] = dist
        return self.distance_cache[key]

    def calculate_route_cost(self, route):
        cost = 0
        for i in range(len(route) - 1):
            cost += self.euclidean_distance(self.nodes[route[i]-1], self.nodes[route[i+1]-1])
        return cost

    def calculate_total_cost(self, routes):
        return sum(self.calculate_route_cost(route) for route in routes)

    def split_algorithm(self, giant_tour):
        n = len(giant_tour)
        if n == 0:
            return [[1, 1]]

        cost = [float('inf')] * (n + 1)
        split_points = [-1] * (n + 1)
        cost[0] = 0

        for i in range(1, n + 1):
            for j in range(max(0, i-150), i):
                route = [1] + giant_tour[j:i] + [1]
                route_demand = sum(self.nodes[cust_id-1]['demand'] for cust_id in giant_tour[j:i])

                if route_demand <= self.capacity:
                    route_cost = self.calculate_route_cost(route)
                    if cost[j] + route_cost < cost[i]:
                        cost[i] = cost[j] + route_cost
                        split_points[i] = j

        routes = []
        idx = n
        while idx > 0:
            start_idx = split_points[idx]
            route = [1] + giant_tour[start_idx:idx] + [1]
            routes.insert(0, route)
            idx = start_idx

        return routes if routes else [[1] + giant_tour + [1]]

    def nearest_neighbor_construction(self, customers):
        if not customers:
            return []
        depot = self.nodes[0]
        unvisited = set(customers)
        tour = [max(unvisited, key=lambda c: self.euclidean_distance(depot, self.nodes[c-1]))]
        unvisited.remove(tour[0])

        while unvisited:
            nearest = min(unvisited, key=lambda c: min(self.euclidean_distance(self.nodes[t-1], self.nodes[c-1]) for t in tour))
            best_pos = 0
            best_increase = float('inf')

            for i in range(len(tour) + 1):
                if i == 0:
                    increase = (self.euclidean_distance(depot, self.nodes[nearest-1]) +
                               self.euclidean_distance(self.nodes[nearest-1], self.nodes[tour[0]-1]) -
                               self.euclidean_distance(depot, self.nodes[tour[0]-1]))
                elif i == len(tour):
                    increase = self.euclidean_distance(self.nodes[tour[-1]-1], self.nodes[nearest-1])
                else:
                    increase = (self.euclidean_distance(self.nodes[tour[i-1]-1], self.nodes[nearest-1]) +
                               self.euclidean_distance(self.nodes[nearest-1], self.nodes[tour[i]-1]) -
                               self.euclidean_distance(self.nodes[tour[i-1]-1], self.nodes[tour[i]-1]))

                if increase < best_increase:
                    best_increase = increase
                    best_pos = i

            tour.insert(best_pos, nearest)
            unvisited.remove(nearest)

        return tour

    def savings_algorithm(self, customers):
        if not customers:
            return []
        depot = self.nodes[0]
        savings = []

        for i in range(len(customers)):
            for j in range(i+1, len(customers)):
                c1, c2 = customers[i], customers[j]
                saving = (self.euclidean_distance(depot, self.nodes[c1-1]) +
                         self.euclidean_distance(depot, self.nodes[c2-1]) -
                         self.euclidean_distance(self.nodes[c1-1], self.nodes[c2-1]))
                savings.append((saving, c1, c2))

        savings.sort(reverse=True)
        routes = [[c] for c in customers]
        route_map = {c: [c] for c in customers}

        for saving, c1, c2 in savings:
            if route_map.get(c1) and route_map.get(c2):
                r1, r2 = route_map[c1], route_map[c2]
                if r1 != r2 and r1[-1] == c1 and r2[0] == c2:
                    merged = r1 + r2
                    for c in merged:
                        route_map[c] = merged
                    routes = [r for r in routes if r != r1 and r != r2]
                    routes.append(merged)

        tour = []
        for route in routes:
            tour.extend(route)
        return tour if tour else customers

    def sweep_algorithm(self, customers):
        if not customers:
            return []
        depot = self.nodes[0]
        angles = [(math.atan2(self.nodes[c-1]['y'] - depot['y'], self.nodes[c-1]['x'] - depot['x']), c) for c in customers]
        angles.sort()
        return [c for _, c in angles]

    def ox_crossover(self, parent1_tour, parent2_tour):
        n = len(parent1_tour)
        if n < 3:
            return parent1_tour.copy()

        segments = random.randint(2, 3)
        points = sorted([0] + [random.randint(1, n-1) for _ in range(segments-1)] + [n])

        child = [None] * n
        for i in range(0, len(points)-1, 2):
            child[points[i]:points[i+1]] = parent1_tour[points[i]:points[i+1]]

        p2_filtered = [x for x in parent2_tour if x not in child]
        idx = 0
        for i in range(n):
            if child[i] is None:
                child[i] = p2_filtered[idx]
                idx += 1

        return child

    def three_opt_improvement(self, routes, max_iterations=300):
        improved = True
        iterations = 0

        while improved and iterations < max_iterations:
            improved = False
            iterations += 1

            for r in range(len(routes)):
                route = routes[r]
                if len(route) < 6:
                    continue

                best_gain = 0.00001
                best_move = None

                for i in range(1, len(route) - 3):
                    for j in range(i + 2, len(route) - 2):
                        for k in range(j + 2, len(route) - 1):
                            current_cost = self.calculate_route_cost(route)

                            candidates = [
                                route[:i] + route[i:j][::-1] + route[j:k+1] + route[k+1:],
                                route[:i] + route[j:k+1][::-1] + route[i:j] + route[k+1:],
                                route[:i] + route[j:k+1] + route[i:j] + route[k+1:],
                                route[:i] + route[i:k+1][::-1] + route[k+1:],
                                route[:i] + route[j:k+1] + route[j:i:-1] + route[k+1:],
                                route[:i] + route[k:j:-1] + route[i:j] + route[k+1:],
                                route[:i] + route[i:j][::-1] + route[k:j:-1] + route[k+1:],
                                route[:i] + route[j:k+1][::-1] + route[i:j][::-1] + route[k+1:],
                                route[:i] + route[k:i:-1] + route[k+1:],
                                route[:i] + route[j:i:-1] + route[k+1:],
                            ]

                            for new_route in candidates:
                                if len(new_route) == len(route):
                                    gain = current_cost - self.calculate_route_cost(new_route)
                                    if gain > best_gain:
                                        best_gain = gain
                                        best_move = new_route

                if best_move:
                    routes[r] = best_move
                    improved = True

        return routes

    def or_opt_improvement(self, routes, max_iterations=200):
        improved = True
        iterations = 0

        while improved and iterations < max_iterations:
            improved = False
            iterations += 1

            for r_idx in range(len(routes)):
                route = routes[r_idx]
                if len(route) < 5:
                    continue

                best_gain = 0.00001
                best_move = None

                for block_size in [1, 2, 3]:
                    for i in range(1, len(route) - block_size - 1):
                        block = route[i:i+block_size]

                        for j in range(1, len(route) - 1):
                            if j >= i and j <= i + block_size:
                                continue

                            new_route = route[:i] + route[i+block_size:]
                            new_route = new_route[:j] + block + new_route[j:]

                            gain = self.calculate_route_cost(route) - self.calculate_route_cost(new_route)
                            if gain > best_gain:
                                best_gain = gain
                                best_move = new_route

                if best_move:
                    routes[r_idx] = best_move
                    improved = True
                    break

        return routes

    def adaptive_local_search(self, routes, intensity='light'):
        current = [r.copy() for r in routes]

        if intensity == 'heavy':
            current = self.three_opt_improvement(current, 300)
            current = self.or_opt_improvement(current, 150)
        elif intensity == 'medium':
            current = self.three_opt_improvement(current, 150)
            current = self.or_opt_improvement(current, 100)
        else:
            current = self.three_opt_improvement(current, 80)

        return current

    def calculate_diversity(self, population):
        if len(population) < 2:
            return 0

        costs = [ind['cost'] for ind in population]
        avg_cost = sum(costs) / len(costs)
        variance = sum((c - avg_cost) ** 2 for c in costs) / len(costs)
        return math.sqrt(variance)

    def adaptive_perturbation(self, routes, strength):
        perturbed = [r.copy() for r in routes]

        for _ in range(strength):
            if len(perturbed) < 2:
                break

            if random.random() < 0.7:
                r1 = random.randint(0, len(perturbed) - 1)
                r2 = random.randint(0, len(perturbed) - 1)

                if r1 != r2 and len(perturbed[r1]) > 3 and len(perturbed[r2]) > 3:
                    positions1 = [random.randint(1, len(perturbed[r1]) - 2) for _ in range(random.randint(1, 2))]
                    positions2 = [random.randint(1, len(perturbed[r2]) - 2) for _ in range(random.randint(1, 2))]

                    for p1, p2 in zip(positions1[:min(len(positions1), len(positions2))], positions2):
                        perturbed[r1][p1], perturbed[r2][p2] = perturbed[r2][p2], perturbed[r1][p1]
            else:
                r = random.randint(0, len(perturbed) - 1)
                route = perturbed[r]

                if len(route) > 10:
                    pos = sorted([random.randint(1, len(route) - 5) for _ in range(4)])
                    if len(set(pos)) == 4:
                        a, b, c, d = pos
                        perturbed[r] = (route[:a] + route[c:d] + route[b:c] +
                                       route[a:b] + route[d:])

        return perturbed

    def generate_initial_population(self, pop_size=1000):
        population = []
        customers = [n['id'] for n in self.nodes if not n['is_depot']]

        construction_methods = [
            lambda: self.nearest_neighbor_construction(customers.copy()),
            lambda: self.savings_algorithm(customers.copy()),
            lambda: self.sweep_algorithm(customers.copy()),
        ]

        for i in range(pop_size):
            method_idx = i % len(construction_methods)
            giant_tour = construction_methods[method_idx]()
            routes = self.split_algorithm(giant_tour)
            improved_routes = self.adaptive_local_search(routes, 'light')
            cost = self.calculate_total_cost(improved_routes)
            population.append({'routes': improved_routes, 'giant_tour': giant_tour, 'cost': cost})

        return population

    def binary_tournament(self, population):
        idx1 = random.randint(0, len(population) - 1)
        idx2 = random.randint(0, len(population) - 1)
        return population[idx1] if population[idx1]['cost'] < population[idx2]['cost'] else population[idx2]

    def solve(self, total_iterations=20000, pop_size=1000, progress_callback=None):
        start_time = time.time()

        population = self.generate_initial_population(pop_size)
        best_individual = min(population, key=lambda x: x['cost'])
        self.best_solution = best_individual
        self.best_cost = best_individual['cost']

        no_improvement_count = 0
        perturbation_counter = 0
        stagnation_threshold = 100

        for iteration in range(total_iterations):
            self.iteration_count = iteration + 1

            parent1 = self.binary_tournament(population)
            parent2 = self.binary_tournament(population)
            child_giant_tour = self.ox_crossover(parent1['giant_tour'], parent2['giant_tour'])

            if not child_giant_tour:
                child_giant_tour = parent1['giant_tour'].copy()
                random.shuffle(child_giant_tour)

            child_routes = self.split_algorithm(child_giant_tour)

            if random.random() < 0.2:
                improved_routes = self.adaptive_local_search(child_routes, 'heavy')
            elif random.random() < 0.5:
                improved_routes = self.adaptive_local_search(child_routes, 'medium')
            else:
                improved_routes = self.adaptive_local_search(child_routes, 'light')

            child_cost = self.calculate_total_cost(improved_routes)

            diversity = self.calculate_diversity(population)

            population.append({'routes': improved_routes, 'giant_tour': child_giant_tour, 'cost': child_cost})
            population.sort(key=lambda x: x['cost'])
            population = population[:pop_size]

            if child_cost < self.best_cost - 0.01:
                self.best_cost = child_cost
                self.best_solution = {'routes': improved_routes, 'giant_tour': child_giant_tour, 'cost': child_cost}
                no_improvement_count = 0
                perturbation_counter = 0
            else:
                no_improvement_count += 1
                perturbation_counter += 1

            if diversity < self.best_cost * 0.002:
                for i in range(min(100, len(population) // 2)):
                    customers = [n['id'] for n in self.nodes if not n['is_depot']]
                    giant_tour = customers.copy()
                    random.shuffle(giant_tour)
                    routes = self.split_algorithm(giant_tour)
                    routes = self.adaptive_local_search(routes, 'medium')
                    cost = self.calculate_total_cost(routes)

                    if cost < population[-(i+1)]['cost']:
                        population[-(i+1)] = {'routes': routes, 'giant_tour': giant_tour, 'cost': cost}
                        population.sort(key=lambda x: x['cost'])

            if perturbation_counter >= stagnation_threshold:
                strength = min(10, perturbation_counter // 30 + 6)

                for i in range(min(50, len(population))):
                    perturbed_routes = self.adaptive_perturbation(population[i]['routes'], strength)
                    perturbed_routes = self.adaptive_local_search(perturbed_routes, 'heavy')
                    perturbed_cost = self.calculate_total_cost(perturbed_routes)

                    if perturbed_cost < population[i]['cost']:
                        population[i]['routes'] = perturbed_routes
                        population[i]['cost'] = perturbed_cost

                perturbation_counter = 0
                stagnation_threshold = max(80, stagnation_threshold - 20)

            self.convergence_history.append({
                'iteration': iteration + 1,
                'best': self.best_cost
            })

            if progress_callback:
                progress_callback(iteration + 1, total_iterations, self.best_cost)

            if no_improvement_count >= 3000:
                break

        self.execution_time = time.time() - start_time
        return self.best_solution


# ===== STREAMLIT ARAYÜZÜ =====
st.set_page_config(page_title="HGS-CVRP v9.1", layout="wide")

st.markdown("""
    <style>
    .main-title {
        text-align: center;
        font-size: 2.5em;
        color: #00D9FF;
        margin-bottom: 0.5em;
        font-weight: bold;
    }
    </style>
    <div class="main-title">🚀 HGS-CVRP v9.1 - ULTRA OPTİMİZE</div>
""", unsafe_allow_html=True)

st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Kontrol Paneli")
    
    # VRP dosyalarını klasörden oto oku
    vrp_files = sorted([f for f in os.listdir('.') if f.endswith('.vrp')])
    
    if not vrp_files:
        st.error("❌ VRP dosyası bulunamadı!")
        st.info("📁 Lütfen .vrp dosyalarını cvrp.py ile aynı klasöre koyun.")
        st.stop()
    
    selected_file = st.selectbox("📁 VRP Dosyası Seç", vrp_files)
    
    col1, col2 = st.columns(2)
    with col1:
        iterations = st.number_input("İterasyonlar", 1000, 50000, 20000, 1000)
    with col2:
        pop_size = st.number_input("Popülasyon", 100, 2000, 1000, 100)
    
    start_button = st.button("▶️ BAŞLAT", use_container_width=True, type="primary")

# Main content
if start_button:
    try:
        st.info(f"📖 {selected_file} yükleniyor...")
        
        solver = CVRPSolver(selected_file)
        
        st.success(f"✅ Problem: {solver.problem_name}")
        st.success(f"   📊 Müşteri: {len(solver.nodes)-1} | Kapasite: {solver.capacity}")
        
        # Progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        metrics_cols = st.columns(3)
        metric_iteration = metrics_cols[0].metric("İterasyon", 0)
        metric_cost = metrics_cols[1].metric("En İyi Maliyet", "---")
        metric_time = metrics_cols[2].metric("Çalışma Süresi", "0.00s")
        
        chart_placeholder = st.empty()
        
        convergence_data = []
        
        def update_progress(iter_num, total, best_cost):
            convergence_data.append({'iteration': iter_num, 'best': best_cost})
            
            progress_bar.progress(iter_num / total)
            status_text.text(f"İterasyon: {iter_num}/{total}")
            
            metrics_cols[0].metric("İterasyon", f"{iter_num:,}")
            metrics_cols[1].metric("En İyi Maliyet", f"{best_cost:.2f}")
            metrics_cols[2].metric("Çalışma Süresi", f"{time.time():.2f}s")
            
            if iter_num % 100 == 0:
                fig, ax = plt.subplots(figsize=(12, 4))
                iters = [d['iteration'] for d in convergence_data]
                costs = [d['best'] for d in convergence_data]
                ax.plot(iters, costs, linewidth=2, color='#00D9FF')
                ax.fill_between(iters, costs, alpha=0.3, color='#00D9FF')
                ax.set_xlabel('İterasyon')
                ax.set_ylabel('Maliyet')
                ax.set_title('Yakınsama Grafiği')
                ax.grid(True, alpha=0.3)
                chart_placeholder.pyplot(fig)
                plt.close()
        
        solution = solver.solve(iterations, pop_size, update_progress)
        
        # Final results
        st.markdown("---")
        st.success(f"✅ TAMAMLANDI ({solver.execution_time:.2f}sn)")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Final Maliyet", f"{solver.best_cost:.2f}")
        col2.metric("Toplam İterasyon", iterations)
        col3.metric("Çalışma Süresi", f"{solver.execution_time:.2f}s")
                # Final graph
        fig, ax = plt.subplots(figsize=(12, 5))
        iters = [d['iteration'] for d in solver.convergence_history]
        costs = [d['best'] for d in solver.convergence_history]
        ax.plot(iters, costs, linewidth=2.5, color='#00D9FF', marker='o', markersize=3)
        ax.fill_between(iters, costs, alpha=0.3, color='#00D9FF')
        ax.set_xlabel('İterasyon', fontsize=12)
        ax.set_ylabel('Maliyet', fontsize=12)
        ax.set_title('Yakınsama Grafiği - Son Sonuç', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
        
    except FileNotFoundError:
        st.error(f"❌ Dosya bulunamadı: {selected_file}")
        st.info("VRP dosyaları ile aynı klasörde olduğundan emin olun.")
    except Exception as e:
        st.error(f"❌ Hata: {str(e)}")
else:
    st.info("👈 Soldaki panelden dosya seçin ve BAŞLAT butonuna tıklayın.")

