class StreamingTravelPlanner {
    constructor() {
        this.apiBaseUrl = window.location.origin;
        this.currentStream = null;
        this.travelData = {};
        
        this.initializeElements();
        this.initializeEventListeners();
        this.initializeTheme();
    }

    initializeElements() {
        // Input elements
        this.messageInput = document.getElementById('queryInput');
        this.chatForm = document.getElementById('chatForm');
        this.sendButton = document.getElementById('searchButton');
        
        // Display elements
        this.progressBar = document.getElementById('progressFill');
        this.progressText = document.getElementById('statusMessage');
        this.progressContainer = document.getElementById('progressContainer');
        this.resultsContainer = document.getElementById('resultsContainer');
        
        // Section containers
        this.summarySection = document.getElementById('summarySection');
        this.flightsSection = document.getElementById('flightsSection');
        this.hotelsSection = document.getElementById('hotelsSection');
        this.attractionsSection = document.getElementById('attractionsSection');
        this.itinerarySection = document.getElementById('itinerarySection');
        this.budgetSection = document.getElementById('budgetSection');
        this.tipsSection = document.getElementById('tipsSection');
        
        // Header elements
        this.clearBtn = document.getElementById('clearBtn');
        this.themeToggle = document.getElementById('themeToggle');
    }

    initializeEventListeners() {
        // Skip form listener if form doesn't exist (using direct button click instead)
        if (this.chatForm) {
            this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        }
        this.clearBtn?.addEventListener('click', () => this.clearResults());
        this.themeToggle?.addEventListener('click', () => this.toggleTheme());
        
        // Sample query buttons
        document.querySelectorAll('.sample-query-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const query = e.target.getAttribute('data-query') || e.target.textContent;
                this.messageInput.value = query;
                this.chatForm.dispatchEvent(new Event('submit'));
            });
        });
    }

    initializeTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const query = this.messageInput.value.trim();
        if (!query) return;
        
        // Disable input
        this.messageInput.disabled = true;
        this.sendButton.disabled = true;
        
        // Clear previous results
        this.clearResults();
        
        // Show results container
        this.resultsContainer.style.display = 'block';
        
        // Start streaming
        this.startStreaming(query);
    }

    async startStreaming(query) {
        try {
            // Disable input
            if (this.messageInput) this.messageInput.disabled = true;
            if (this.sendButton) this.sendButton.disabled = true;
            
            // Clear previous results
            this.clearResults();
            
            // Show progress and results containers
            if (this.progressContainer) this.progressContainer.style.display = 'block';
            if (this.resultsContainer) this.resultsContainer.style.display = 'block';
            
            // Close any existing stream
            if (this.currentStream) {
                this.currentStream.close();
            }
            
            // Create request body
            const response = await fetch(`${this.apiBaseUrl}/api/v1/travel/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: query })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Create EventSource for streaming
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) {
                    console.log('Stream complete');
                    break;
                }
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                
                // Process complete lines
                for (let i = 0; i < lines.length - 1; i++) {
                    const line = lines[i].trim();
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.substring(6));
                        this.handleStreamData(data);
                    }
                }
                
                // Keep the last incomplete line in buffer
                buffer = lines[lines.length - 1];
            }
            
        } catch (error) {
            console.error('Streaming error:', error);
            this.showError(`Failed to create travel plan: ${error.message}`);
        } finally {
            // Re-enable input
            if (this.messageInput) this.messageInput.disabled = false;
            if (this.sendButton) this.sendButton.disabled = false;
        }
    }

    handleStreamData(data) {
        console.log('Received stream data:', data);
        
        // Update progress
        if (data.progress) {
            this.updateProgress(data.progress, data.message || 'Processing...');
        }
        
        // Handle different data types
        switch (data.type) {
            case 'status':
                this.showStatus(data.message);
                break;
                
            case 'summary':
                this.displaySummary(data.data);
                break;
                
            case 'flights':
                this.displayFlights(data.data);
                break;
                
            case 'hotels':
                this.displayHotels(data.data);
                break;
                
            case 'attractions':
                this.displayAttractions(data.data);
                break;
                
            case 'itinerary':
                this.displayItinerary(data.data);
                break;
                
            case 'budget':
                this.displayBudget(data.data);
                break;
                
            case 'tips':
                this.displayTips(data.data);
                break;
                
            case 'complete':
                this.onStreamComplete();
                break;
                
            case 'error':
                this.showError(data.message);
                break;
        }
    }

    updateProgress(percentage, message) {
        if (this.progressBar) {
            this.progressBar.style.width = `${percentage}%`;
            this.progressBar.textContent = `${percentage}%`;
            this.progressBar.setAttribute('aria-valuenow', percentage);
        }
        if (this.progressText) {
            this.progressText.textContent = message;
        }
    }

    showStatus(message) {
        const statusDiv = document.createElement('div');
        statusDiv.className = 'status-message fade-in';
        statusDiv.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${message}`;
        
        const statusContainer = document.getElementById('statusContainer');
        if (statusContainer) {
            statusContainer.innerHTML = '';
            statusContainer.appendChild(statusDiv);
        }
    }

    displaySummary(summary) {
        if (!this.summarySection) return;
        
        this.summarySection.style.display = 'block';
        this.summarySection.innerHTML = `
            <div class="section-card fade-in">
                <div class="section-header">
                    <h3><i class="fas fa-map-marked-alt"></i> Trip Summary</h3>
                </div>
                <div class="summary-content">
                    <div class="summary-route">
                        <span class="origin">${summary.origin}</span>
                        <i class="fas fa-plane animated-plane"></i>
                        <span class="destination">${summary.destination}</span>
                    </div>
                    <div class="summary-details">
                        <div class="detail-item">
                            <i class="fas fa-calendar-alt"></i>
                            <span>${new Date(summary.departure_date).toLocaleDateString()}</span>
                        </div>
                        <div class="detail-item">
                            <i class="fas fa-clock"></i>
                            <span>${summary.duration_days} ${summary.duration_days === 1 ? 'day' : 'days'}</span>
                        </div>
                        <div class="detail-item">
                            <i class="fas fa-users"></i>
                            <span>${summary.travelers} ${summary.travelers === 1 ? 'traveler' : 'travelers'}</span>
                        </div>
                        <div class="detail-item">
                            <i class="fas fa-tag"></i>
                            <span>${summary.travel_type}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    displayFlights(flights) {
        if (!this.flightsSection) return;
        
        this.flightsSection.style.display = 'block';
        
        let flightsHTML = `
            <div class="section-card fade-in">
                <div class="section-header">
                    <h3><i class="fas fa-plane"></i> Flight Options</h3>
                    <span class="badge">${flights.total_options} flights found</span>
                </div>
        `;
        
        // Outbound flights
        if (flights.outbound && flights.outbound.length > 0) {
            flightsHTML += `
                <div class="flights-container">
                    <h4>Outbound Flights</h4>
                    <div class="flights-grid">
            `;
            
            flights.outbound.forEach(flight => {
                flightsHTML += this.createFlightCard(flight);
            });
            
            flightsHTML += '</div></div>';
        }
        
        // Return flights
        if (flights.return && flights.return.length > 0) {
            flightsHTML += `
                <div class="flights-container">
                    <h4>Return Flights</h4>
                    <div class="flights-grid">
            `;
            
            flights.return.forEach(flight => {
                flightsHTML += this.createFlightCard(flight);
            });
            
            flightsHTML += '</div></div>';
        }
        
        flightsHTML += '</div>';
        this.flightsSection.innerHTML = flightsHTML;
    }

    createFlightCard(flight) {
        const departureTime = new Date(flight['Departure']);
        const arrivalTime = new Date(flight['Arrival']);
        const price = parseFloat(flight['Total Price']) || 0;
        
        return `
            <div class="flight-card slide-in">
                <div class="flight-header">
                    <div class="airline-info">
                        <span class="airline-name">${flight['Airline Name']}</span>
                        <span class="airline-code">${flight['Airline Code']}</span>
                    </div>
                    <div class="flight-price">
                        <span class="price">₹${price.toLocaleString()}</span>
                        <span class="price-note">per person</span>
                    </div>
                </div>
                <div class="flight-route">
                    <div class="route-time">
                        <span class="time">${departureTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                    </div>
                    <div class="route-line">
                        <div class="line"></div>
                        <span class="stops">${flight['Number of Stops'] === 0 ? 'Direct' : `${flight['Number of Stops']} stop(s)`}</span>
                    </div>
                    <div class="route-time">
                        <span class="time">${arrivalTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                    </div>
                </div>
            </div>
        `;
    }

    displayHotels(hotels) {
        if (!this.hotelsSection) return;
        
        this.hotelsSection.style.display = 'block';
        
        let hotelsHTML = `
            <div class="section-card fade-in">
                <div class="section-header">
                    <h3><i class="fas fa-bed"></i> Accommodation Options</h3>
                    <span class="badge">${hotels.total_options} hotels found</span>
                </div>
                <div class="hotels-grid">
        `;
        
        if (hotels.options && hotels.options.length > 0) {
            hotels.options.forEach(hotel => {
                const price = parseFloat(hotel['Total Price']) || 0;
                hotelsHTML += `
                    <div class="hotel-card slide-in">
                        <div class="hotel-header">
                            <h4 class="hotel-name">${hotel['Hotel Name']}</h4>
                            <div class="hotel-rating">${hotel['Rating'] !== 'N/A' ? '⭐'.repeat(Math.floor(parseFloat(hotel['Rating']))) : 'No rating'}</div>
                        </div>
                        <div class="hotel-details">
                            <div class="detail">
                                <i class="fas fa-map-marker-alt"></i>
                                <span>${hotel['City']}</span>
                            </div>
                            <div class="detail">
                                <i class="fas fa-bed"></i>
                                <span>${hotel['Room Type']}</span>
                            </div>
                        </div>
                        <div class="hotel-footer">
                            <span class="price">₹${price.toLocaleString()}/night</span>
                        </div>
                    </div>
                `;
            });
        } else {
            hotelsHTML += '<p>No hotels found for your criteria. Try adjusting your search.</p>';
        }
        
        hotelsHTML += '</div></div>';
        this.hotelsSection.innerHTML = hotelsHTML;
    }

    displayAttractions(attractions) {
        if (!this.attractionsSection) return;
        
        this.attractionsSection.style.display = 'block';
        
        let attractionsHTML = `
            <div class="section-card fade-in">
                <div class="section-header">
                    <h3><i class="fas fa-map-signs"></i> Things to Do</h3>
                </div>
        `;
        
        // Must visit places
        if (attractions.must_visit && attractions.must_visit.length > 0) {
            attractionsHTML += `
                <div class="attractions-container">
                    <h4>Must Visit Places</h4>
                    <div class="attractions-grid">
            `;
            
            attractions.must_visit.forEach(place => {
                attractionsHTML += `
                    <div class="attraction-card slide-in">
                        <div class="attraction-header">
                            <h5>${place.name}</h5>
                            <span class="category">${place.category}</span>
                        </div>
                        <p>${place.description}</p>
                    </div>
                `;
            });
            
            attractionsHTML += '</div></div>';
        }
        
        // Dining
        if (attractions.dining && attractions.dining.length > 0) {
            attractionsHTML += `
                <div class="dining-container">
                    <h4>Where to Eat</h4>
                    <div class="dining-grid">
            `;
            
            attractions.dining.forEach(restaurant => {
                attractionsHTML += `
                    <div class="dining-card slide-in">
                        <div class="dining-header">
                            <h5>${restaurant.name}</h5>
                            <span class="cuisine">${restaurant.cuisine_type}</span>
                        </div>
                        <p>${restaurant.description}</p>
                        <span class="price-range">${restaurant.price_range}</span>
                    </div>
                `;
            });
            
            attractionsHTML += '</div></div>';
        }
        
        attractionsHTML += '</div>';
        this.attractionsSection.innerHTML = attractionsHTML;
    }

    displayItinerary(itinerary) {
        if (!this.itinerarySection || !itinerary || itinerary.length === 0) return;
        
        this.itinerarySection.style.display = 'block';
        
        let itineraryHTML = `
            <div class="section-card fade-in">
                <div class="section-header">
                    <h3><i class="fas fa-calendar-alt"></i> Day-by-Day Itinerary</h3>
                </div>
                <div class="itinerary-timeline">
        `;
        
        itinerary.forEach(day => {
            itineraryHTML += `
                <div class="itinerary-day slide-in">
                    <div class="day-header">
                        <div class="day-number">Day ${day.day_number}</div>
                        <div class="day-theme">${day.theme}</div>
                    </div>
                    <div class="day-activities">
            `;
            
            if (day.activities) {
                day.activities.forEach(activity => {
                    itineraryHTML += `
                        <div class="activity-item">
                            <span class="activity-time">${activity.time}</span>
                            <span class="activity-name">${activity.name}</span>
                        </div>
                    `;
                });
            }
            
            itineraryHTML += '</div></div>';
        });
        
        itineraryHTML += '</div></div>';
        this.itinerarySection.innerHTML = itineraryHTML;
    }

    displayBudget(budget) {
        if (!this.budgetSection) return;
        
        this.budgetSection.style.display = 'block';
        
        this.budgetSection.innerHTML = `
            <div class="section-card fade-in">
                <div class="section-header">
                    <h3><i class="fas fa-calculator"></i> Budget Estimate</h3>
                </div>
                <div class="budget-content">
                    <div class="budget-total">
                        <div class="total-amount">
                            <span class="currency">₹</span>
                            <span class="amount">${budget.total.toLocaleString()}</span>
                        </div>
                        <div class="per-person">₹${budget.per_person.toLocaleString()} per person</div>
                    </div>
                    <div class="budget-breakdown">
                        <div class="breakdown-item">
                            <span class="item-name"><i class="fas fa-plane"></i> Flights</span>
                            <span class="item-amount">₹${budget.flights.toLocaleString()}</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="item-name"><i class="fas fa-bed"></i> Accommodation</span>
                            <span class="item-amount">₹${budget.accommodation.toLocaleString()}</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="item-name"><i class="fas fa-utensils"></i> Food & Activities</span>
                            <span class="item-amount">₹${budget.activities_food.toLocaleString()}</span>
                        </div>
                        <div class="breakdown-item">
                            <span class="item-name"><i class="fas fa-car"></i> Local Transport</span>
                            <span class="item-amount">₹${budget.local_transport.toLocaleString()}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    displayTips(tips) {
        if (!this.tipsSection) return;
        
        this.tipsSection.style.display = 'block';
        
        this.tipsSection.innerHTML = `
            <div class="section-card fade-in">
                <div class="section-header">
                    <h3><i class="fas fa-lightbulb"></i> Travel Tips</h3>
                </div>
                <div class="tips-grid">
                    <div class="tip-card">
                        <h4><i class="fas fa-cloud-sun"></i> Best Time to Visit</h4>
                        <p>${tips.best_time_to_visit}</p>
                    </div>
                    <div class="tip-card">
                        <h4><i class="fas fa-suitcase"></i> What to Pack</h4>
                        <ul>
                            ${tips.what_to_pack.map(item => `<li>${item}</li>`).join('')}
                        </ul>
                    </div>
                    <div class="tip-card">
                        <h4><i class="fas fa-shield-alt"></i> Safety Tips</h4>
                        <p>${tips.safety_tips}</p>
                    </div>
                    <div class="tip-card">
                        <h4><i class="fas fa-money-bill-wave"></i> Money Tips</h4>
                        <p>${tips.money_tips}</p>
                    </div>
                </div>
            </div>
        `;
    }

    onStreamComplete() {
        this.updateProgress(100, 'Your travel plan is ready!');
        
        // Add completion animation
        setTimeout(() => {
            if (this.progressBar) {
                this.progressBar.parentElement.classList.add('complete');
            }
        }, 500);
        
        // Show success notification
        this.showNotification('Travel plan created successfully!', 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
        this.updateProgress(0, 'Error occurred');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type} slide-in`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'check-circle'}"></i>
            <span>${message}</span>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    clearResults() {
        // Clear all sections
        const sections = [
            this.summarySection,
            this.flightsSection,
            this.hotelsSection,
            this.attractionsSection,
            this.itinerarySection,
            this.budgetSection,
            this.tipsSection
        ];
        
        sections.forEach(section => {
            if (section) {
                section.style.display = 'none';
                section.innerHTML = '';
            }
        });
        
        // Reset progress
        this.updateProgress(0, '');
        
        // Clear travel data
        this.travelData = {};
    }
}

// Initialize the app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.streamingTravel = new StreamingTravelPlanner();
});

// Export for use in other scripts
window.StreamingTravelPlanner = StreamingTravelPlanner;