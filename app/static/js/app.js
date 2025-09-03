class FlightChatbot {
    constructor() {
        this.sessionId = null;
        this.isTyping = false;
        this.apiBaseUrl = window.location.origin;
        this.currentFlights = [];
        
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
        
        // Results elements
        this.flightResults = document.getElementById('flightResults');
        this.flightsList = document.getElementById('flightsList');
        
        // Header elements
        this.clearChatBtn = document.getElementById('clearChat');
        this.toggleThemeBtn = document.getElementById('toggleTheme');
        this.connectionStatus = document.getElementById('connectionStatus');
        
        // Modal elements
        this.flightModal = document.getElementById('flightModal');
    }

    initializeEventListeners() {
        // Chat form listeners
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        this.messageInput.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.messageInput.addEventListener('input', () => this.autoResize());
        
        // Header listeners
        this.clearChatBtn.addEventListener('click', () => this.clearChat());
        this.toggleThemeBtn.addEventListener('click', () => this.toggleTheme());
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
            const response = await fetch(`${this.apiBaseUrl}/api/health/`);
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

        try {
            const response = await this.sendMessage(message);
            this.hideTypingIndicator();
            
            if (response.response) {
                // Debug logging
                console.log('Response received:', response);
                console.log('Flight data:', response.flight_data);
                console.log('Show flight cards:', response.show_flight_cards);
                
                // Display combined message with recommendations and flight cards
                this.addMessage(response.response, 'assistant', response.flight_data, response.show_flight_cards);
            }
            
            if (response.flight_data && response.flight_data.length > 0) {
                this.currentFlights = response.flight_data;
            }
            
            if (response.session_id) {
                this.sessionId = response.session_id;
            }
        } catch (error) {
            this.hideTypingIndicator();
            this.showError('Failed to send message. Please try again.');
        }
    }

    async sendMessage(message) {
        const response = await fetch(`${this.apiBaseUrl}/api/chat/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: this.sessionId
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    displayFlightResults(flights) {
        if (!this.flightResults || !this.flightsList) return;
        
        this.flightResults.style.display = 'block';
        this.flightsList.innerHTML = '';
        
        flights.forEach((flight, index) => {
            const flightCard = this.createFlightCard(flight, index);
            this.flightsList.appendChild(flightCard);
        });
    }
    
    createFlightCard(flight, index) {
        const card = document.createElement('div');
        card.className = 'flight-card';
        
        const departureTime = new Date(flight['Departure']);
        const arrivalTime = new Date(flight['Arrival']);
        
        // Calculate flight duration
        const durationMs = arrivalTime.getTime() - departureTime.getTime();
        const durationHours = Math.floor(durationMs / (1000 * 60 * 60));
        const durationMins = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));
        const durationText = `${durationHours}h ${durationMins}m`;
        
        // Convert price to INR if EUR
        const priceInINR = flight['Currency'] === 'EUR' ? Math.floor(flight['Total Price'] * 90) : flight['Total Price'];
        const currency = flight['Currency'] === 'EUR' ? '₹' : flight['Currency'];
        
        card.innerHTML = `
            <div class="mmt-flight-card">
                <div class="flight-header">
                    <div class="airline-info">
                        <div class="airline-logo">${flight['Airline Code'] || 'AI'}</div>
                        <div class="airline-details">
                            <div class="airline-name">${flight['Airline Name'] || 'Air India'}</div>
                            <div class="flight-code">${flight['Airline Code'] || 'AI'}-${Math.floor(Math.random() * 9000) + 1000}</div>
                        </div>
                    </div>
                    <div class="flight-badges">
                        ${flight['Number of Stops'] === 0 ? '<span class="badge non-stop">Non stop</span>' : `<span class="badge stops">${flight['Number of Stops']} stop</span>`}
                    </div>
                </div>
                
                <div class="flight-route-info">
                    <div class="departure">
                        <div class="time">${departureTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                        <div class="date">${departureTime.toLocaleDateString('en-GB', {day: 'numeric', month: 'short'})}</div>
                        <div class="airport">BOM</div>
                    </div>
                    
                    <div class="flight-duration-info">
                        <div class="duration">${durationText}</div>
                        <div class="route-line">
                            <div class="line"></div>
                            <div class="stops-info">${flight['Number of Stops'] === 0 ? 'Direct' : `${flight['Number of Stops']} stop`}</div>
                        </div>
                    </div>
                    
                    <div class="arrival">
                        <div class="time">${arrivalTime.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                        <div class="date">${arrivalTime.toLocaleDateString('en-GB', {day: 'numeric', month: 'short'})}</div>
                        <div class="airport">DEL</div>
                    </div>
                </div>
                
                <div class="flight-pricing">
                    <div class="price-info">
                        <div class="price">${currency} ${priceInINR.toLocaleString()}</div>
                        <div class="price-note">per adult</div>
                    </div>
                    <button class="book-now-btn">
                        BOOK NOW
                    </button>
                </div>
            </div>
        `;
        
        // Add event listener for book button
        const bookBtn = card.querySelector('.book-now-btn');
        if (bookBtn) {
            bookBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showFlightDetails(flight);
            });
        }
        
        return card;
    }
    

    addMessage(text, sender, flightData = null, showFlightCards = false) {
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
        senderName.textContent = sender === 'user' ? 'You' : 'Assistant';
        
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
        
        // Debug logging for flight cards
        console.log('addMessage called with:', { showFlightCards, flightData, flightDataLength: flightData ? flightData.length : 0 });
        
        // Add flight cards FIRST if requested and data is available
        if (showFlightCards && flightData && flightData.length > 0) {
            console.log('Creating flight cards...');
            const flightCardsContainer = document.createElement('div');
            flightCardsContainer.className = 'inline-flight-results';
            
            const cardsHeader = document.createElement('div');
            cardsHeader.className = 'inline-results-header';
            cardsHeader.innerHTML = `
                <h4><i class="fas fa-plane"></i> Available Flights</h4>
            `;
            flightCardsContainer.appendChild(cardsHeader);
            
            const cardsList = document.createElement('div');
            cardsList.className = 'inline-flights-list';
            
            flightData.forEach((flight, index) => {
                const flightCard = this.createFlightCard(flight, index);
                cardsList.appendChild(flightCard);
            });
            
            flightCardsContainer.appendChild(cardsList);
            content.appendChild(flightCardsContainer);
        }
        
        // Then add the recommendations text below the cards
        content.appendChild(messageText);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        const welcomeMessage = this.chatMessages.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    showFlightDetails(flight) {
        const modalBody = document.getElementById('modalBody');
        const departureTime = new Date(flight['Departure']);
        const arrivalTime = new Date(flight['Arrival']);
        
        if (modalBody) {
            modalBody.innerHTML = `
                <div class="flight-detail">
                    <h4>Flight Information</h4>
                    <dl>
                        <dt>Airline:</dt>
                        <dd>${flight['Airline Name'] || flight['Airline Code']}</dd>
                        
                        <dt>Departure:</dt>
                        <dd>${departureTime.toLocaleString()}</dd>
                        
                        <dt>Arrival:</dt>
                        <dd>${arrivalTime.toLocaleString()}</dd>
                        
                        <dt>Price:</dt>
                        <dd>${flight['Currency']} ${flight['Total Price']}</dd>
                        
                        <dt>Cabin Class:</dt>
                        <dd>${flight['Cabin'] || 'Economy'}</dd>
                        
                        <dt>Stops:</dt>
                        <dd>${flight['Number of Stops'] === 0 ? 'Direct Flight' : `${flight['Number of Stops']} Stop(s)`}</dd>
                        
                        <dt>Trip Type:</dt>
                        <dd>${flight['One Way'] ? 'One Way' : 'Round Trip'}</dd>
                    </dl>
                </div>
            `;
        }
        
        this.flightModal.classList.add('active');
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

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
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
            display: flex;
            align-items: center;
            gap: 0.5rem;
            max-width: 400px;
        `;
        
        notification.innerHTML = `
            <i class="fas fa-${type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
            <button onclick="this.parentElement.remove()" style="background: none; border: none; color: var(--text-secondary); cursor: pointer; margin-left: auto;">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    async clearChat() {
        if (!confirm('Are you sure you want to clear the chat history?')) return;
        
        if (this.sessionId) {
            try {
                await fetch(`${this.apiBaseUrl}/api/chat/session/${this.sessionId}`, {
                    method: 'DELETE'
                });
            } catch (error) {
                console.error('Failed to clear session:', error);
            }
        }
        
        this.sessionId = null;
        this.chatMessages.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">
                    <i class="fas fa-plane-departure"></i>
                </div>
                <h2>Flight Booking Assistant</h2>
                <p>I can help you find and compare flights. Just tell me:</p>
                <div class="features-list">
                    <div class="feature-item">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>Where you want to go</span>
                    </div>
                    <div class="feature-item">
                        <i class="fas fa-calendar-alt"></i>
                        <span>When you want to travel</span>
                    </div>
                    <div class="feature-item">
                        <i class="fas fa-users"></i>
                        <span>Number of passengers</span>
                    </div>
                </div>
                <div class="example-queries">
                    <h3>Try asking:</h3>
                    <button class="example-btn" onclick="sendExampleQuery('Find me flights from New York to London on December 15, 2024')">
                        <i class="fas fa-quote-left"></i>
                        Find me flights from New York to London on December 15, 2024
                    </button>
                    <button class="example-btn" onclick="sendExampleQuery('Show me the cheapest flights from Delhi to Mumbai next week')">
                        <i class="fas fa-quote-left"></i>
                        Show me the cheapest flights from Delhi to Mumbai next week
                    </button>
                    <button class="example-btn" onclick="sendExampleQuery('I need 2 tickets from San Francisco to Tokyo next Monday')">
                        <i class="fas fa-quote-left"></i>
                        I need 2 tickets from San Francisco to Tokyo next Monday
                    </button>
                </div>
            </div>
        `;
        
        if (this.flightResults) {
            this.flightResults.style.display = 'none';
        }
    }
}

// Global functions
function sendExampleQuery(query) {
    const input = document.getElementById('messageInput');
    input.value = query;
    input.focus();
    document.getElementById('chatForm').dispatchEvent(new Event('submit'));
}

function closeFlightModal() {
    document.getElementById('flightModal').classList.remove('active');
}

function closeComparisonModal() {
    document.getElementById('comparisonModal').classList.remove('active');
}

function scrollToSection(sectionId) {
    if (window.flightApp) {
        window.flightApp.scrollToSection(sectionId);
    }
}

function toggleFilters() {
    if (window.flightApp) {
        window.flightApp.toggleFilters();
    }
}

function toggleFlightComparison(index) {
    // Implementation for flight comparison
    console.log('Toggle comparison for flight', index);
}

function shareFlightDetails(index) {
    // Implementation for sharing flight details
    if (navigator.share) {
        navigator.share({
            title: 'Flight Details',
            text: 'Check out this flight I found!',
            url: window.location.href
        });
    } else {
        // Fallback - copy to clipboard
        navigator.clipboard.writeText(window.location.href);
        if (window.flightApp) {
            window.flightApp.showNotification('Flight details copied to clipboard!', 'success');
        }
    }
}

// Additional helper functions
function addSuggestion(text) {
    const input = document.getElementById('messageInput');
    input.value = text + ' ';
    input.focus();
}

document.addEventListener('DOMContentLoaded', () => {
    window.chatbot = new FlightChatbot();
    
    setInterval(() => {
        window.chatbot.checkConnection();
    }, 30000);
});