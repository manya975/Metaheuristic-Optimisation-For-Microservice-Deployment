import random
import requests
import xmltodict

def fetch_service_node_mapping(eureka_server_url):
    try:
        response = requests.get(f"{eureka_server_url}/eureka/apps")
        response.raise_for_status()

        data = xmltodict.parse(response.text)
        service_node_mapping = {}

        applications = data.get('applications', {}).get('application', [])
        for app in applications:
            service_name = app.get('name')
            instances = app.get('instance')

            if isinstance(instances, dict):
                instances = [instances]

            nodes = []
            for instance in instances:
                instance_id = instance.get('instanceId')
                if instance_id:
                    nodes.append(instance_id)

            if service_name and nodes:
                service_node_mapping[service_name] = nodes

        return service_node_mapping

    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        return {}
    except xmltodict.expat.ExpatError as e:
        print(f"Failed to parse response: {e}")
        return {}

def generate_chromosome(service_node_mapping):
    return [random.choice(nodes) if nodes else None for nodes in service_node_mapping.values()]

def fitness(chromosome, service_node_mapping):
    total_latency = 0
    unique_nodes = set(chromosome)

    for i in range(len(chromosome)):
        for j in range(i + 1, len(chromosome)):
            if chromosome[i] is None or chromosome[j] is None:
                total_latency += 1000
            elif chromosome[i] == chromosome[j]:
                total_latency += 5
            else:
                latency = random.randint(40, 100)
                total_latency += latency

    diversity_penalty = (len(service_node_mapping) - len(unique_nodes)) * 50
    total_latency += diversity_penalty
    return total_latency

def selection(population, fitness_scores):
    sorted_population = [x for _, x in sorted(zip(fitness_scores, population), key=lambda pair: pair[0])]
    return sorted_population[:2]

def crossover(parent1, parent2):
    child1, child2 = [], []
    for i in range(len(parent1)):
        if random.random() > 0.5:
            child1.append(parent1[i])
            child2.append(parent2[i])
        else:
            child1.append(parent2[i])
            child2.append(parent1[i])
    return child1, child2

def mutate(chromosome, service_node_mapping, mutation_rate=0.2):
    for i in range(len(chromosome)):
        if random.random() < mutation_rate:
            service_name = list(service_node_mapping.keys())[i]
            available_nodes = service_node_mapping[service_name]
            if available_nodes:
                chromosome[i] = random.choice(available_nodes)
    return chromosome

def validate_fault_tolerance(chromosome, service_node_mapping):
    for service, nodes in service_node_mapping.items():
        assigned_nodes = [node for node in chromosome if node in nodes]
        if len(set(assigned_nodes)) < 1:  # At least one node must be assigned per service
            return False
    return True

def genetic_algorithm_with_eureka(eureka_server_url, population_size=10, generations=50):
    service_node_mapping = fetch_service_node_mapping(eureka_server_url)
    if not service_node_mapping:
        print("Failed to fetch service-node mapping or data is empty.")
        return None

    population = [generate_chromosome(service_node_mapping) for _ in range(population_size)]

    for generation in range(generations):
        fitness_scores = [fitness(chromosome, service_node_mapping) for chromosome in population]
        parents = selection(population, fitness_scores)
        child1, child2 = crossover(parents[0], parents[1])
        child1 = mutate(child1, service_node_mapping)
        child2 = mutate(child2, service_node_mapping)
        population[-2:] = [child1, child2]

        best_fitness = min(fitness_scores)
        print(f"Generation {generation + 1} | Best Fitness: {best_fitness}")

    best_solution = min(population, key=lambda x: fitness(x, service_node_mapping))

    if validate_fault_tolerance(best_solution, service_node_mapping):
        return best_solution
    else:
        print("No fault-tolerant solution found.")
        return None

if __name__ == "__main__":
    eureka_server_url = "http://localhost:8761"  

    best_solution = genetic_algorithm_with_eureka(eureka_server_url, population_size=20, generations=100)

    if best_solution:
        print("Best Node Configuration:", best_solution)
        print("Best Fitness (latency):", fitness(best_solution, fetch_service_node_mapping(eureka_server_url)))
        print("Fault Tolerance Validation: PASS")
    else:
        print("Failed to find a fault-tolerant configuration.")
