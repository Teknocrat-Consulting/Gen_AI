class TravelPlannerApp {
    constructor() {
        this.sessionId = null;
        this.isTyping = false;
        this.apiBaseUrl = window.location.origin;
        this.currentItinerary = null;
        
        this.initializeElements();
        this.initializeEventListeners();
        this.initializeTheme();
        this.checkConnection();
    }

    initializeElements() {
        // Chat elements
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.chatForm = document.getElementById('chatForm');
        this.sendButton = document.getElementById('sendButton');
        this.typingIndicator = document.getElementById('typingIndicator');
        
        // Header elements
        this.clearChatBtn = document.getElementById('clearChat');
        this.toggleThemeBtn = document.getElementById('toggleTheme');
        this.connectionStatus = document.getElementById('connectionStatus');
        
        // Results container
        this.resultsContainer = document.getElementById('resultsContainer');
    }

    initializeEventListeners() {
        // Chat form listeners
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        this.messageInput.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.messageInput.addEventListener('input', () => this.autoResize());
        
        // Header listeners
        this.clearChatBtn.addEventListener('click', () => this.clearChat());
        this.toggleThemeBtn.addEventListener('click', () => this.toggleTheme());
        
        // Sample query buttons
        document.querySelectorAll('.sample-query-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const query = e.target.getAttribute('data-query');
                this.sendSampleQuery(query);
            });
        });
    }

    initializeTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        this.updateThemeIcon(savedTheme);
    }
    
    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        this.updateThemeIcon(newTheme);
    }

    updateThemeIcon(theme) {
        const icon = this.toggleThemeBtn.querySelector('i');
        icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }

    async checkConnection() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/v1/travel/health`);
            if (response.ok) {
                this.setConnectionStatus(true);
            } else {
                this.setConnectionStatus(false);
            }
        } catch (error) {
            this.setConnectionStatus(false);
        }
    }

    setConnectionStatus(connected) {
        const statusText = this.connectionStatus.querySelector('span');
        if (connected) {
            this.connectionStatus.classList.add('connected');
            this.connectionStatus.classList.remove('disconnected');
            statusText.textContent = 'Connected';
        } else {
            this.connectionStatus.classList.remove('connected');
            this.connectionStatus.classList.add('disconnected');
            statusText.textContent = 'Disconnected';
        }
    }

    handleKeydown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.chatForm.dispatchEvent(new Event('submit'));
        }
    }

    autoResize() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    async handleSubmit(e) {
        e.preventDefault();
        
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;

        this.addMessage(message, 'user');
        this.messageInput.value = '';
        this.autoResize();
        this.showTypingIndicator();
        this.hideWelcomeMessage();

        try {
            const response = await this.createTravelPlan(message);
            this.hideTypingIndicator();
            
            if (response.success) {
                this.currentItinerary = response.data;
                this.addMessage('✈️ Perfect! I\'ve created your complete travel itinerary:', 'assistant');
                this.displayTravelPlan(response);
            } else {
                this.addMessage(response.error || 'Sorry, I couldn\'t create your travel plan. Please try again with more specific details.', 'assistant');
            }
            
        } catch (error) {
            this.hideTypingIndicator();
            this.showError('Failed to create travel plan. Please try again.');
        }
    }

    async createTravelPlan(query) {
        const response = await fetch(`${this.apiBaseUrl}/api/v1/travel/plan-simple`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: this.sessionId
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    displayTravelPlan(response) {
        const data = response.data || response;
        
        // Create travel plan container
        const planContainer = document.createElement('div');
        planContainer.className = 'travel-plan-container';
        
        // Trip Summary
        this.addTripSummary(planContainer, data.summary);
        
        // Flights Section
        if (data.flights && (data.flights.outbound.length > 0 || data.flights.return.length > 0)) {
            this.addFlightsSection(planContainer, data.flights);
        }
        
        // Hotels Section
        if (data.hotels && data.hotels.options.length > 0) {
            this.addHotelsSection(planContainer, data.hotels);
        }
        
        // Attractions Section
        if (data.attractions) {
            this.addAttractionsSection(planContainer, data.attractions);
        }
        
        // Itinerary Section
        if (data.itinerary && data.itinerary.length > 0) {
            this.addItinerarySection(planContainer, data.itinerary);
        }
        
        // Budget Section
        if (data.budget) {
            this.addBudgetSection(planContainer, data.budget);
        }
        
        // Tips Section
        if (data.tips) {
            this.addTipsSection(planContainer, data.tips);
        }
        
        this.chatMessages.appendChild(planContainer);
        this.scrollToBottom();
    }

    addTripSummary(container, summary) {
        const summaryDiv = document.createElement('div');
        summaryDiv.className = 'travel-summary-card';
        summaryDiv.innerHTML = `
            <div class="summary-header">
                <h3><i class="fas fa-map-marked-alt"></i> Trip Summary</h3>
            </div>
            <div class="summary-content">
                <div class="summary-route">
                    <span class="origin">${summary.origin}</span>
                    <i class="fas fa-arrow-right"></i>
                    <span class="destination">${summary.destination}</span>
                </div>
                <div class="summary-details">
                    <div class="detail-item">
                        <i class="fas fa-calendar-alt"></i>
                        <span>${new Date(summary.departure_date).toLocaleDateString('en-GB', { 
                            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' 
                        })}</span>
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
                        <span class="travel-type">${summary.travel_type} trip</span>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(summaryDiv);
    }

    addFlightsSection(container, flights) {
        const flightsDiv = document.createElement('div');
        flightsDiv.className = 'flights-section';
        
        let flightsHTML = `
            <div class="section-header">
                <h3><i class="fas fa-plane"></i> Flight Options</h3>
                <span class="results-count">${flights.total_options} options found</span>
            </div>
        `;
        
        // Outbound flights
        if (flights.outbound.length > 0) {
            flightsHTML += '<div class="flight-direction"><h4>Outbound Flights</h4><div class="flights-grid">';
            flights.outbound.forEach(flight => {
                flightsHTML += this.createFlightCardHTML(flight);
            });
            flightsHTML += '</div></div>';
        }
        
        // Return flights
        if (flights.return.length > 0) {
            flightsHTML += '<div class="flight-direction"><h4>Return Flights</h4><div class="flights-grid">';
            flights.return.forEach(flight => {
                flightsHTML += this.createFlightCardHTML(flight);
            });
            flightsHTML += '</div></div>';
        }
        
        flightsDiv.innerHTML = flightsHTML;
        container.appendChild(flightsDiv);
    }

    createFlightCardHTML(flight) {
        const departureTime = new Date(flight['Departure']);
        const arrivalTime = new Date(flight['Arrival']);
        
        const durationMs = arrivalTime.getTime() - departureTime.getTime();
        const durationHours = Math.floor(durationMs / (1000 * 60 * 60));
        const durationMins = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));
        
        const price = parseFloat(flight['Total Price']);
        const currency = flight['Currency'] === 'EUR' ? '₹' : flight['Currency'];
        const displayPrice = flight['Currency'] === 'EUR' ? Math.floor(price * 90) : price;
        
        return `
            <div class="flight-card">
                <div class="flight-header">
                    <div class="airline-info">
                        <span class="airline-name">${flight['Airline Name']}</span>
                        <span class="airline-code">${flight['Airline Code']}</span>
                    </div>
                    <div class="flight-price">
                        <span class="price">${currency}${displayPrice.toLocaleString()}</span>
                        <span class="price-note">per person</span>
                    </div>
                </div>
                <div class="flight-route">
                    <div class="route-time">
                        <span class="time">${departureTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                        <span class="date">${departureTime.toLocaleDateString('en-GB', {day: 'numeric', month: 'short'})}</span>
                    </div>
                    <div class="route-info">
                        <div class="duration">${durationHours}h ${durationMins}m</div>
                        <div class="stops">${flight['Number of Stops'] === 0 ? 'Direct' : `${flight['Number of Stops']} stop(s)`}</div>
                    </div>
                    <div class="route-time">
                        <span class="time">${arrivalTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                        <span class="date">${arrivalTime.toLocaleDateString('en-GB', {day: 'numeric', month: 'short'})}</span>
                    </div>
                </div>
                <div class="flight-actions">
                    <button class="btn-outline" onclick="showFlightDetails('${flight['Airline Code']}')">
                        <i class="fas fa-info-circle"></i> Details
                    </button>
                    <button class="btn-primary">
                        <i class="fas fa-calendar-check"></i> Book Now
                    </button>
                </div>
            </div>
        `;
    }

    addHotelsSection(container, hotels) {
        const hotelsDiv = document.createElement('div');
        hotelsDiv.className = 'hotels-section';
        
        let hotelsHTML = `
            <div class="section-header">
                <h3><i class="fas fa-bed"></i> Hotel Options</h3>
                <span class="results-count">${hotels.total_options} options found</span>
            </div>
            <div class="hotels-grid">
        `;
        
        hotels.options.slice(0, 6).forEach(hotel => {
            const price = parseFloat(hotel['Total Price']) || 0;
            const currency = hotel['Currency'] || '₹';
            const rating = hotel['Rating'] && hotel['Rating'] !== 'N/A' ? parseFloat(hotel['Rating']) : 0;
            const stars = rating > 0 ? '★'.repeat(Math.floor(rating)) : 'No rating';
            
            hotelsHTML += `
                <div class="hotel-card">
                    <div class="hotel-header">
                        <h4 class="hotel-name">${hotel['Hotel Name']}</h4>
                        <div class="hotel-rating">${stars}</div>
                    </div>
                    <div class="hotel-details">
                        <div class="hotel-location">
                            <i class="fas fa-map-marker-alt"></i>
                            <span>${hotel['City']}</span>
                        </div>
                        <div class="room-type">
                            <i class="fas fa-bed"></i>
                            <span>${hotel['Room Type']}</span>
                        </div>
                        <div class="hotel-amenities">
                            <i class="fas fa-wifi"></i>
                            <span>${hotel['Amenities'].split(',').slice(0, 2).join(', ')}</span>
                        </div>
                    </div>
                    <div class="hotel-footer">
                        <div class="hotel-price">
                            <span class="price">${currency}${price.toLocaleString()}</span>
                            <span class="price-note">per night</span>
                        </div>
                        <button class="btn-primary">
                            <i class="fas fa-calendar-check"></i> Book Now
                        </button>
                    </div>
                </div>
            `;
        });
        
        hotelsHTML += '</div>';
        hotelsDiv.innerHTML = hotelsHTML;
        container.appendChild(hotelsDiv);
    }

    addAttractionsSection(container, attractions) {
        const attractionsDiv = document.createElement('div');
        attractionsDiv.className = 'attractions-section';
        
        let attractionsHTML = `
            <div class="section-header">
                <h3><i class="fas fa-map-signs"></i> Things to Do</h3>
            </div>
        `;
        
        // Must Visit Attractions
        if (attractions.must_visit && attractions.must_visit.length > 0) {
            attractionsHTML += `
                <div class="attractions-category">
                    <h4><i class="fas fa-star"></i> Must Visit Places</h4>
                    <div class="attractions-grid">
            `;
            
            attractions.must_visit.forEach(attraction => {
                attractionsHTML += `
                    <div class="attraction-card">
                        <div class="attraction-header">
                            <h5>${attraction.name}</h5>
                            <span class="category">${attraction.category}</span>
                        </div>
                        <div class="attraction-content">
                            <p>${attraction.description}</p>
                            <div class="attraction-meta">
                                <span class="time"><i class="fas fa-clock"></i> ${attraction.estimated_time}h</span>
                                <span class="best-time"><i class="fas fa-sun"></i> ${attraction.best_time}</span>
                            </div>
                        </div>
                    </div>
                `;
            });
            attractionsHTML += '</div></div>';
        }
        
        // Experiences
        if (attractions.experiences && attractions.experiences.length > 0) {
            attractionsHTML += `
                <div class="attractions-category">
                    <h4><i class="fas fa-heart"></i> Local Experiences</h4>
                    <div class="experiences-grid">
            `;
            
            attractions.experiences.forEach(experience => {
                attractionsHTML += `
                    <div class="experience-card">
                        <div class="experience-header">
                            <h5>${experience.name}</h5>
                            <span class="type">${experience.type}</span>
                        </div>
                        <div class="experience-content">
                            <p>${experience.description}</p>
                            <div class="experience-meta">
                                <span class="duration"><i class="fas fa-clock"></i> ${experience.duration}h</span>
                                <span class="cost"><i class="fas fa-rupee-sign"></i> ${experience.cost_estimate}</span>
                            </div>
                        </div>
                    </div>
                `;
            });
            attractionsHTML += '</div></div>';
        }
        
        // Dining
        if (attractions.dining && attractions.dining.length > 0) {
            attractionsHTML += `
                <div class="attractions-category">
                    <h4><i class="fas fa-utensils"></i> Where to Eat</h4>
                    <div class="dining-grid">
            `;
            
            attractions.dining.forEach(restaurant => {
                attractionsHTML += `
                    <div class="dining-card">
                        <div class="dining-header">
                            <h5>${restaurant.name}</h5>
                            <span class="cuisine">${restaurant.cuisine_type}</span>
                        </div>
                        <div class="dining-content">
                            <p>${restaurant.description}</p>
                            <div class="dining-meta">
                                <span class="price-range">${restaurant.price_range}</span>
                                <span class="meal-type">${restaurant.meal_type}</span>
                            </div>
                            <div class="must-try">
                                <strong>Must try:</strong> ${restaurant.must_try_dishes.join(', ')}
                            </div>
                        </div>
                    </div>
                `;
            });
            attractionsHTML += '</div></div>';
        }
        
        attractionsDiv.innerHTML = attractionsHTML;
        container.appendChild(attractionsDiv);
    }

    addItinerarySection(container, itinerary) {
        const itineraryDiv = document.createElement('div');
        itineraryDiv.className = 'itinerary-section';
        
        let itineraryHTML = `
            <div class="section-header">
                <h3><i class="fas fa-calendar-alt"></i> Day-by-Day Itinerary</h3>
            </div>
            <div class="itinerary-timeline">
        `;
        
        itinerary.forEach((day, index) => {
            itineraryHTML += `
                <div class="itinerary-day">
                    <div class="day-header">
                        <div class="day-number">Day ${day.day_number}</div>
                        <div class="day-info">
                            <h4>${day.theme}</h4>
                            <span class="day-date">${new Date(day.date).toLocaleDateString('en-GB', { 
                                weekday: 'long', month: 'long', day: 'numeric' 
                            })}</span>
                        </div>
                        <div class="day-budget">
                            <span class="budget">₹${day.budget_estimate}</span>
                        </div>
                    </div>
                    <div class="day-content">
                        <div class="activities-list">
            `;
            
            if (day.activities && day.activities.length > 0) {
                day.activities.forEach(activity => {
                    itineraryHTML += `
                        <div class="activity-item">
                            <div class="activity-time">${activity.time}</div>
                            <div class="activity-details">
                                <h5>${activity.name}</h5>
                                <p>${activity.description}</p>
                                <span class="activity-duration">${activity.duration}</span>
                            </div>
                        </div>
                    `;
                });
            }
            
            itineraryHTML += `
                        </div>
                        <div class="day-meals">
                            <h5><i class="fas fa-utensils"></i> Meals</h5>
                            <div class="meals-list">
            `;
            
            if (day.meals && day.meals.length > 0) {
                day.meals.forEach(meal => {
                    itineraryHTML += `
                        <div class="meal-item">
                            <span class="meal-time">${meal.time}</span>
                            <span class="meal-restaurant">${meal.restaurant}</span>
                            <span class="meal-cost">${meal.estimated_cost}</span>
                        </div>
                    `;
                });
            }
            
            itineraryHTML += `
                            </div>
                        </div>
                        <div class="day-tips">
                            <h5><i class="fas fa-lightbulb"></i> Tips</h5>
                            <p>${day.tips}</p>
                        </div>
                    </div>
                </div>
            `;
        });
        
        itineraryHTML += '</div>';
        itineraryDiv.innerHTML = itineraryHTML;
        container.appendChild(itineraryDiv);
    }

    addBudgetSection(container, budget) {
        const budgetDiv = document.createElement('div');
        budgetDiv.className = 'budget-section';
        
        budgetDiv.innerHTML = `
            <div class="section-header">
                <h3><i class="fas fa-calculator"></i> Budget Estimate</h3>
            </div>
            <div class="budget-content">
                <div class="budget-total">
                    <div class="total-amount">
                        <span class="amount">₹${budget.total.toLocaleString()}</span>
                        <span class="note">Total for ${budget.total > 0 ? Math.round(budget.total / budget.per_person) : 1} travelers</span>
                    </div>
                    <div class="per-person">
                        <span class="amount">₹${budget.per_person.toLocaleString()}</span>
                        <span class="note">per person</span>
                    </div>
                </div>
                <div class="budget-breakdown">
                    <div class="breakdown-item">
                        <div class="item-info">
                            <i class="fas fa-plane"></i>
                            <span>Flights</span>
                        </div>
                        <span class="item-amount">₹${budget.flights.toLocaleString()}</span>
                    </div>
                    <div class="breakdown-item">
                        <div class="item-info">
                            <i class="fas fa-bed"></i>
                            <span>Hotels</span>
                        </div>
                        <span class="item-amount">₹${budget.accommodation.toLocaleString()}</span>
                    </div>
                    <div class="breakdown-item">
                        <div class="item-info">
                            <i class="fas fa-utensils"></i>
                            <span>Food & Activities</span>
                        </div>
                        <span class="item-amount">₹${budget.activities_food.toLocaleString()}</span>
                    </div>
                    <div class="breakdown-item">
                        <div class="item-info">
                            <i class="fas fa-car"></i>
                            <span>Local Transport</span>
                        </div>
                        <span class="item-amount">₹${budget.local_transport.toLocaleString()}</span>
                    </div>
                </div>
            </div>
        `;
        
        container.appendChild(budgetDiv);
    }

    addTipsSection(container, tips) {
        const tipsDiv = document.createElement('div');
        tipsDiv.className = 'tips-section';
        
        tipsDiv.innerHTML = `
            <div class="section-header">
                <h3><i class="fas fa-lightbulb"></i> Travel Tips</h3>
            </div>
            <div class="tips-grid">
                <div class="tip-card">
                    <h4><i class="fas fa-suitcase-rolling"></i> Packing</h4>
                    <ul>
                        ${tips.what_to_pack && tips.what_to_pack.length > 0 ? 
                            tips.what_to_pack.map(item => `<li>${item}</li>`).join('') : 
                            '<li>Pack light and comfortable clothes</li><li>Don\'t forget essentials like chargers</li>'
                        }
                    </ul>
                </div>
                <div class="tip-card">
                    <h4><i class="fas fa-money-bill-wave"></i> Money Tips</h4>
                    <p>${tips.money_tips || 'Carry some cash along with cards. Check for local payment methods.'}</p>
                </div>
                <div class="tip-card">
                    <h4><i class="fas fa-shield-alt"></i> Safety</h4>
                    <p>${tips.safety_tips || 'Keep important documents safe. Stay aware of your surroundings.'}</p>
                </div>
                <div class="tip-card">
                    <h4><i class="fas fa-comments"></i> Local Culture</h4>
                    <p>${tips.local_customs || 'Be respectful of local customs and traditions.'}</p>
                </div>
            </div>
        `;
        
        container.appendChild(tipsDiv);
    }

    addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = sender === 'user' ? 
            '<i class="fas fa-user"></i>' : 
            '<i class="fas fa-robot"></i>';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        const header = document.createElement('div');
        header.className = 'message-header';
        
        const senderName = document.createElement('span');
        senderName.className = 'message-sender';
        senderName.textContent = sender === 'user' ? 'You' : 'Travel Assistant';
        
        const time = document.createElement('span');
        time.className = 'message-time';
        time.textContent = new Date().toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        header.appendChild(senderName);
        header.appendChild(time);
        
        const messageText = document.createElement('div');
        messageText.className = 'message-text';
        messageText.textContent = text;
        
        content.appendChild(header);
        content.appendChild(messageText);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showTypingIndicator() {
        this.isTyping = true;
        this.typingIndicator.classList.add('active');
        this.sendButton.disabled = true;
    }

    hideTypingIndicator() {
        this.isTyping = false;
        this.typingIndicator.classList.remove('active');
        this.sendButton.disabled = false;
    }

    hideWelcomeMessage() {
        const welcomeMessage = this.chatMessages.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.style.display = 'none';
        }
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.style.cssText = `
            position: fixed;
            top: 2rem;
            right: 2rem;
            background: var(--surface);
            border: 2px solid var(--${type === 'error' ? 'error' : 'primary'}-color);
            color: var(--text-primary);
            padding: 1rem 1.5rem;
            border-radius: var(--radius);
            box-shadow: var(--shadow-lg);
            z-index: 1001;
            max-width: 400px;
        `;
        
        notification.innerHTML = `
            <i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    sendSampleQuery(query) {
        this.messageInput.value = query;
        this.messageInput.focus();
        this.chatForm.dispatchEvent(new Event('submit'));
    }

    clearChat() {
        if (!confirm('Are you sure you want to clear the chat?')) return;
        
        this.currentItinerary = null;
        this.chatMessages.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-header">
                    <div class="welcome-icon">
                        <i class="fas fa-route"></i>
                    </div>
                    <h2>AI Travel Planner</h2>
                    <p>Your personal travel agent powered by AI</p>
                </div>
                
                <div class="welcome-features">
                    <div class="feature-card">
                        <i class="fas fa-plane"></i>
                        <h3>Complete Itinerary</h3>
                        <p>Flights, hotels, attractions, and day-by-day plans</p>
                    </div>
                    <div class="feature-card">
                        <i class="fas fa-calculator"></i>
                        <h3>Budget Planning</h3>
                        <p>Detailed cost breakdown for your entire trip</p>
                    </div>
                    <div class="feature-card">
                        <i class="fas fa-map-marked-alt"></i>
                        <h3>Local Insights</h3>
                        <p>Attractions, dining, and cultural experiences</p>
                    </div>
                </div>
                
                <div class="sample-queries">
                    <h3>Try asking:</h3>
                    <button class="sample-query-btn" data-query="I want to go from Mumbai to Delhi next Monday for 2 days, 2 people">
                        Mumbai to Delhi next Monday, 2 days, 2 people
                    </button>
                    <button class="sample-query-btn" data-query="Plan a romantic weekend trip from Bangalore to Goa for 2 adults">
                        Romantic weekend to Goa from Bangalore
                    </button>
                    <button class="sample-query-btn" data-query="Family vacation from Pune to Jaipur next month for 4 days, 4 people">
                        Family trip to Jaipur, 4 days, 4 people
                    </button>
                </div>
            </div>
        `;
    }
}

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    window.travelPlanner = new TravelPlannerApp();
    
    // Check connection periodically
    setInterval(() => {
        window.travelPlanner.checkConnection();
    }, 30000);
});

// Global utility functions
function showFlightDetails(airlineCode) {
    console.log('Showing flight details for:', airlineCode);
}

function showHotelDetails(hotelId) {
    console.log('Showing hotel details for:', hotelId);
}