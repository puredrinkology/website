document.addEventListener('DOMContentLoaded', function() {
    let idx = null;  // Lunr index
    let searchResults = document.getElementById('search-results');
    let data = null; // Store search index data

    // Fetch search index JSON
    fetch('/searchindex/index.json')
        .then(response => response.json())
        .then(fetchedData => {
            data = fetchedData;  // Assign data to a higher scope
            // Create the Lunr index
            idx = lunr(function () {
                this.field('title');
                this.field('base_spirit');
                this.field('description');
                this.field('family');
                this.field('category');
                this.field('ingredient_items');
                this.ref('url');
                
                data.forEach(doc => {
                    this.add(doc);
                });
            });
        })
        .catch(error => console.error('Error fetching search index:', error));

    // Debounce function
    function debounce(func, delay) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // Search function
    const performSearch = debounce(function(query) {
        if (idx && query.length > 2) {
            const results = idx.search(query);
            searchResults.innerHTML = '';  // Clear previous results

            if (results.length) {
                results.forEach(result => {
                    const url = result.ref;
                    const item = data.find(i => i.url === url); // Now data is available here
                    const cover = item.url + "images/cover.jpeg";

                    searchResults.innerHTML += `
                        <div class="col-12 col-md-6 col-lg-2 mb-4">
                            <div class="card shadow border-0 p-4 text-decoration-none h-100" style="border-radius: 15px;">
                                <a class="aspect-ratio-full" href="${url}">
                                    ${cover ? `<img class="rounded-10" src="${cover}" alt="${item.title}" />` : ''}
                                </a>
                                <div class="card-body text-center">
                                    <h5 class="card-title fw-semibold">
                                        <a href="${url}" class="text-decoration-none">${item.title}</a>
                                    </h5>
                                    ${item.category ? `<a href="/recipes/category/${item.category.toLowerCase()}/" class="badge text-bg-primary text-decoration-none">${item.category.toLowerCase()}</a>` : ''}
                                    ${item.base_spirit ? `<a href="/recipes/spirit/${item.base_spirit.toLowerCase()}/" class="badge text-bg-secondary text-decoration-none">${item.base_spirit.toLowerCase()}</a>` : ''}
                                    ${item.family ? `<a href="/recipes/family/${item.family.toLowerCase()}/" class="badge text-bg-info text-decoration-none">${item.family.toLowerCase()}</a>` : ''}
                                </div>
                            </div>
                        </div>
                    `;
                });
            } else {
                searchResults.innerHTML = '';
            }
        } else {
            searchResults.innerHTML = '';
        }
    }, 300); // Adjust the delay as needed

    // Input event listener with debounced search
    document.getElementById('search-box').addEventListener('input', function() {
        const query = this.value;
        performSearch(query);  // Call the debounced search function
    });
});
